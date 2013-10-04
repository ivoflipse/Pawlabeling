import numpy as np
from collections import defaultdict
from PySide import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pubsub import pub
from pawlabeling.functions import utility, calculations
from pawlabeling.settings import settings
from pawlabeling.models import model


class ForceViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(ForceViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
        self.parent = parent
        self.active = False

        self.left_front = ContactView(self, label="Left Front", contact_label=0)
        self.left_hind = ContactView(self, label="Left Hind", contact_label=1)
        self.right_front = ContactView(self, label="Right Front", contact_label=2)
        self.right_hind = ContactView(self, label="Right Hind", contact_label=3)

        self.contacts_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
        }

        self.contacts = defaultdict(list)

        self.left_contacts_layout = QtGui.QVBoxLayout()
        self.left_contacts_layout.addWidget(self.left_front)
        self.left_contacts_layout.addWidget(self.left_hind)
        self.right_contacts_layout = QtGui.QVBoxLayout()
        self.right_contacts_layout.addWidget(self.right_front)
        self.right_contacts_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_contacts_layout)
        self.main_layout.addLayout(self.right_contacts_layout)
        self.setLayout(self.main_layout)

        pub.subscribe(self.change_frame, "analysis.change_frame")
        pub.subscribe(self.active_widget, "active_widget")

    def change_frame(self, frame):
        for contact_label, widget in self.contacts_list.iteritems():
            if self.active:
                widget.change_frame(frame)
            else:
                widget.frame = frame

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            for contact_label, widget in self.contacts_list.iteritems():
                widget.draw()


class ContactView(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(ContactView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.contact_label = contact_label
        self.parent = parent
        self.model = model.model
        self.frame = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.x = 100
        self.y = 100
        self.filtered = []
        self.outlier_toggle = False

        self.dpi = 100
        self.fig = Figure(figsize=(3.0, 2.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(0)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.canvas)
        self.main_layout.setStretchFactor(self.canvas, 3)
        height = settings.settings.contacts_widget_height()
        self.setMinimumHeight(height)
        self.setLayout(self.main_layout)

        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.update_results, "update_results")
        pub.subscribe(self.filter_outliers, "filter_outliers")
        pub.subscribe(self.update_contact, "update_contact")

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        self.draw()

    def update_results(self, results, max_results):
        self.forces = results[self.contact_label]["force"]
        self.max_duration = max_results["duration"]
        self.max_force = max_results["force"]
        self.filtered = results[self.contact_label]["filtered"]
        if self.parent.active:
            self.draw()

    def update_contact(self):
        if self.contact_label == self.model.contact.contact_label:
            if self.parent.active:
                self.draw()

    def draw(self):
        if not self.model.contacts:
            return

        self.clear_axes()
        interpolate_length = 100
        lengths = []

        force_over_time = []
        self.max_duration = 0
        self.max_force = 0

        for measurement_name, contacts in self.model.contacts.iteritems():
            for contact in contacts:
                if contact.contact_label == self.contact_label:
                    force = np.pad(contact.force_over_time, 1, mode="constant", constant_values=0)
                    if len(force) > self.max_duration:
                        self.max_duration = len(force)
                    if np.max(force) > self.max_force:
                        self.max_force = np.max(force)

                    lengths.append(len(force))
                    interpolated_force = calculations.interpolate_time_series(force, interpolate_length)
                    force_over_time.append(interpolated_force)
                    time_line = calculations.interpolate_time_series(np.arange(np.max(len(force))),
                                                                     interpolate_length)
                    self.axes.plot(time_line, interpolated_force, alpha=0.5)

        # If there's a contact selected, plot that too
        if self.contact_label in self.model.selected_contacts:
            contact = self.model.selected_contacts[self.contact_label]
            force = np.pad(contact.force_over_time, 1, mode="constant", constant_values=0)
            interpolated_force = calculations.interpolate_time_series(force, interpolate_length)
            time_line = calculations.interpolate_time_series(np.arange(np.max(len(force))),
                                                             interpolate_length)
            self.axes.plot(time_line, interpolated_force, color="k", linewidth=4, alpha=0.75)


        # If this is empty, there were no contacts to plot
        if not force_over_time:
            return
        force_over_time = np.array(force_over_time)
        mean_length = np.mean(lengths)
        interpolated_time_line = calculations.interpolate_time_series(np.arange(int(mean_length)), interpolate_length)
        mean_force = np.mean(force_over_time, axis=0)
        std_force = np.std(force_over_time, axis=0)
        self.axes.plot(interpolated_time_line, mean_force, color="r", linewidth=3)
        self.axes.plot(interpolated_time_line, mean_force + std_force, color="r", linewidth=1)
        self.axes.fill_between(interpolated_time_line, mean_force - std_force, mean_force + std_force, facecolor="r",
                               alpha=0.5)
        self.axes.plot(interpolated_time_line, mean_force - std_force, color="r", linewidth=1)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(self.frame)
        self.axes.set_xlim([0, self.max_duration + 2])  # +2 because we padded the array
        self.axes.set_ylim([0, self.max_force * 1.2])
        self.canvas.draw()


    def change_frame(self, frame):
        self.frame = frame
        self.vertical_line.set_xdata(self.frame)
        #self.canvas.draw()
        self.canvas.draw_idle()

    def clear_axes(self):
        self.axes.cla()
        self.canvas.draw()

    def clear_cached_values(self):
        # Put the screen to black
        self.clear_axes()
        self.forces = None
        self.max_duration = None
        self.max_force = None
        self.filtered = None
