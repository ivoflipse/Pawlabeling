import numpy as np
from PySide import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pubsub import pub
from ...functions import utility, calculations
from ...settings import settings
from ...models import model


class PressureViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(PressureViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Pressure View")
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
            progress = 0
            pub.sendMessage("update_progress", progress=progress)
            for contact_label, widget in self.contacts_list.iteritems():
                widget.draw()
                progress += 25
                pub.sendMessage("update_progress", progress=progress)
            pub.sendMessage("update_progress", progress=100)


class ContactView(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(ContactView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.contact_label = contact_label
        self.parent = parent
        self.model = model.model
        self.frame = 0
        self.x = 0
        self.y = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.outlier_toggle = False

        self.dpi = 100
        self.fig = Figure((3.0, 2.0), dpi=self.dpi)
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
        pub.subscribe(self.filter_outliers, "filter_outliers")
        pub.subscribe(self.update_contact, "put_contact")

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        self.draw()

    def update_contact(self):
        if self.contact_label == self.model.contact.contact_label:
            if self.parent.active:
                self.draw()

    def draw(self):
        # If there's no measurement_data, return
        if not self.model.contacts:
            return

        self.clear_axes()
        interpolate_length = 100
        lengths = []
        pressure_over_time = []
        self.max_duration = 0
        self.max_pressure = 0

        for measurement_name, contacts in self.model.contacts.iteritems():
            for contact in contacts:
                # Skip contacts that have been filtered if the toggle is on
                if self.outlier_toggle:
                    if contact.filtered or contact.invalid:
                        continue
                if contact.contact_label == self.contact_label:
                    pressure = np.pad(contact.pressure_over_time, 1, mode="constant", constant_values=0)
                    if len(pressure) > self.max_duration:
                        self.max_duration = len(pressure)
                    if np.max(pressure) > self.max_pressure:
                        self.max_pressure = np.max(pressure)

                    lengths.append(len(pressure))
                    interpolated_pressure = calculations.interpolate_time_series(pressure, interpolate_length)
                    pressure_over_time.append(interpolated_pressure)
                    time_line = calculations.interpolate_time_series(np.arange(np.max(len(pressure))),
                                                                     interpolate_length)
                    self.axes.plot(time_line, interpolated_pressure, alpha=0.5)

        # If there's a contact selected, plot that too
        if self.contact_label in self.model.selected_contacts:
            contact = self.model.selected_contacts[self.contact_label]
            pressure = np.pad(contact.pressure_over_time, 1, mode="constant", constant_values=0)
            interpolated_pressure = calculations.interpolate_time_series(pressure, interpolate_length)
            time_line = calculations.interpolate_time_series(np.arange(np.max(len(pressure))),
                                                             interpolate_length)
            self.axes.plot(time_line, interpolated_pressure, color="k", linewidth=4, alpha=0.75)

        # If this is empty, there were no contacts to plot
        if not pressure_over_time:
            return
        pressure_over_time = np.array(pressure_over_time)
        mean_length = np.mean(lengths)
        interpolated_time_line = calculations.interpolate_time_series(np.arange(int(mean_length)), interpolate_length)
        mean_pressure = np.mean(pressure_over_time, axis=0)
        std_pressure = np.std(pressure_over_time, axis=0)
        self.axes.plot(interpolated_time_line, mean_pressure, color="r", linewidth=3)
        self.axes.plot(interpolated_time_line, mean_pressure + std_pressure, color="r", linewidth=1)
        self.axes.fill_between(interpolated_time_line, mean_pressure - std_pressure, mean_pressure + std_pressure,
                               facecolor="r", alpha=0.5)
        self.axes.plot(interpolated_time_line, mean_pressure - std_pressure, color="r", linewidth=1)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(self.frame)
        self.axes.set_xlim([0, self.model.max_length + 2])  # +2 because we padded the array
        self.axes.set_ylim([0, self.max_pressure * 1.2])
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
        self.pressures = None
        self.max_duration = None
        self.max_pressure = None
