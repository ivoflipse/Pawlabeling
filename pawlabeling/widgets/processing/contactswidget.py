import logging
from collections import defaultdict
from itertools import izip
from PySide import QtGui
import numpy as np
from pubsub import pub
from pawlabeling.functions import utility, calculations
from pawlabeling.settings import settings
from pawlabeling.models import model


class ContactWidgets(QtGui.QWidget):
    def __init__(self, parent):
        super(ContactWidgets, self).__init__(parent)
        self.parent = parent
        self.model = model.model

        self.left_front = ContactWidget(self, label="Left Front", contact_label=0)
        self.left_hind = ContactWidget(self, label="Left Hind", contact_label=1)
        self.right_front = ContactWidget(self, label="Right Front", contact_label=2)
        self.right_hind = ContactWidget(self, label="Right Hind", contact_label=3)
        self.current_contact = ContactWidget(self, label="", contact_label=-1)

        self.average_data = defaultdict(list)

        self.contacts_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
            -1: self.current_contact
        }

        self.logger = logging.getLogger("logger")
        self.settings = settings.settings
        self.contact_dict = self.settings.contact_dict

        self.left_contacts_layout = QtGui.QVBoxLayout()
        self.left_contacts_layout.addWidget(self.left_front)
        self.left_contacts_layout.addWidget(self.left_hind)
        self.current_contact_layout = QtGui.QVBoxLayout()
        self.current_contact_layout.addStretch(1)
        self.current_contact_layout.addWidget(QtGui.QLabel("Current contact"))
        self.current_contact_layout.addWidget(self.current_contact)
        self.current_contact_layout.setStretchFactor(self.current_contact, 3)
        self.current_contact_layout.addStretch(1)
        self.right_contacts_layout = QtGui.QVBoxLayout()
        self.right_contacts_layout.addWidget(self.right_front)
        self.right_contacts_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_contacts_layout)
        self.main_layout.addLayout(self.current_contact_layout)
        self.main_layout.addLayout(self.right_contacts_layout)
        self.setLayout(self.main_layout)

        # TODO I might have to unsubscribe these as well...
        pub.subscribe(self.update_contacts, "update_current_contact")

    def update_contacts(self):
        # Clear any previous results, which may be out of date
        self.clear_contacts()

        # Update those for which we have a average measurement_data
        for contact_label, average_contact in self.model.average_data.iteritems():
            widget = self.contacts_list[contact_label]
            widget.update(average_contact)

        # Update the current contact widget
        widget = self.contacts_list[-1]
        current_contact = self.model.contacts[self.model.measurement_name][self.model.current_contact_index]

        x, y, z = current_contact.data.shape
        self.mx, self.my, self.mz = self.model.shape
        normalized_current_contact = np.zeros((self.mx, self.my, self.mz))
        offset_x = int((self.mx - x) / 2)
        offset_y = int((self.my - y) / 2)
        normalized_current_contact[offset_x:offset_x + x, offset_y:offset_y + y, 0:z] = current_contact.data

        widget.update(normalized_current_contact)

        try:
            self.predict_label()
        except Exception as e:
            self.logger.info("Couldn't predict the labels. Exception: {}".format(e))

    # TODO predict label should receive the average data and compute on that
    def predict_label(self):
        current_contact = self.contacts_list[-1]
        # If there's no measurement_data, we can quit
        if current_contact.max_pressure == float("inf"):
            return

        pressure = current_contact.max_pressure
        surface = current_contact.mean_surface
        duration = current_contact.mean_duration
        data = current_contact.data

        pressures = []
        surfaces = []
        durations = []
        data_list = []
        # Then iterate through the other contacts
        for contact_label, contact in list(self.contacts_list.iteritems()):
            # Skip comparing with yourself
            if contact_label == -1:
                continue
            pressures.append(contact.max_pressure)
            surfaces.append(contact.mean_surface)
            durations.append(contact.mean_duration)
            data_list.append(contact.data)

        # For each value calculate how much % it varies
        if all([pressure, surface, duration, data_list]):
            percentages_pressures = [np.sqrt((p - pressure) ** 2) / pressure for p in pressures]
            percentages_surfaces = [np.sqrt((s - surface) ** 2) / surface for s in surfaces]
            percentages_durations = [np.sqrt((d - duration) ** 2) / duration for d in durations]
            percentages_data = [np.sum(np.sqrt((d - data) ** 2)) / np.sum(np.sum(data)) for d in data_list]
            results = []
            for p, s, d, d2 in izip(percentages_pressures, percentages_surfaces, percentages_durations,
                                   percentages_data):
                results.append(p + s + d + d2)

            best_result = np.argmin(results)
            current_contact.label_prediction.setText("{}".format(self.contact_dict[best_result]))

    def clear_contacts(self):
        for contact_label, widget in self.contacts_list.iteritems():
            widget.clear_cached_values()


class ContactWidget(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(ContactWidget, self).__init__(parent)
        self.parent = parent
        self.model = model.model
        self.settings = settings.settings
        self.degree = self.settings.interpolation_contact_widgets()
        self.n_max = 0
        self.label = label
        self.contact_label = contact_label
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 1
        self.my = 1
        self.mz = 1
        self.data = np.zeros((self.mx, self.my))
        self.average_data = np.zeros((self.mx, self.my, self.mz))

        self.scene = QtGui.QGraphicsScene(self)
        self.view = ContactView(contact_label=self.contact_label, parent=self.scene)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.max_pressure = float("inf")
        self.mean_duration = float("inf")
        self.mean_surface = float("inf")

        self.label_prediction = QtGui.QLabel(self)
        self.max_pressure_label = QtGui.QLabel(self)
        self.mean_duration_label = QtGui.QLabel(self)
        self.mean_surface_label = QtGui.QLabel(self)

        self.label_prediction.setText("{}".format(self.label))
        self.max_pressure_label.setText("{} N".format(0 if self.max_pressure == float("inf") else self.max_pressure))
        self.mean_duration_label.setText(
            "{} frames".format(0 if self.mean_duration == float("inf") else self.mean_duration))
        self.mean_surface_label.setText(
            "{} pixels".format(0 if self.mean_surface == float("inf") else self.mean_surface))

        self.number_layout = QtGui.QVBoxLayout()
        self.number_layout.addWidget(self.label_prediction)
        self.number_layout.addWidget(self.max_pressure_label)
        self.number_layout.addWidget(self.mean_duration_label)
        self.number_layout.addWidget(self.mean_surface_label)
        self.number_layout.addStretch(1)

        self.main_layout = QtGui.QHBoxLayout(self)
        self.main_layout.addWidget(self.view)
        self.main_layout.addLayout(self.number_layout)

        self.setMinimumHeight(self.settings.contacts_widget_height())
        self.setLayout(self.main_layout)

        pub.subscribe(self.update_n_max, "update_n_max")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")

    def update_n_max(self):
        # Redraw, just in case
        self.redraw()

    # TODO Don't do any calculations you don't have to!
    def update(self, average_data):
        # Calculate an average contact from the list of arrays
        self.average_data = average_data
        self.max_pressure = np.max(calculations.force_over_time(self.average_data))
        x, y, z = np.nonzero(self.average_data)
        self.mean_duration = np.max(z)
        self.mean_surface = np.max(
            calculations.pixel_count_over_time(self.average_data) * self.model.plate.sensor_surface)

        self.max_pressure_label.setText("{:3.1f} N".format(self.max_pressure))
        self.mean_duration_label.setText("{} frames".format(int(self.mean_duration)))
        self.mean_surface_label.setText("{:3.1f} pixels".format(self.mean_surface))

        # Make sure the contacts are facing upright
        self.data = np.rot90(np.rot90(self.average_data.max(axis=2)))[:, ::-1]
        self.pixmap = utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table,
                                          interpolation="cubic")
        self.image.setPixmap(self.pixmap)
        self.resizeEvent()

    def redraw(self):
        self.pixmap = utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table,
                                          interpolation="cubic")
        self.image.setPixmap(self.pixmap)
        self.resizeEvent()

    def clear_cached_values(self):
        self.data = np.zeros((self.mx, self.my))
        self.average_data = []
        # Put the screen to black
        self.image.setPixmap(utility.get_qpixmap(np.zeros((15, 15)), self.degree, self.n_max, self.color_table))
        self.max_pressure = float("inf")
        self.mean_duration = float("inf")
        self.mean_surface = float("inf")

        self.label_prediction.setText("{}".format(self.label))
        self.max_pressure_label.setText("{} N".format(0 if self.max_pressure == float("inf") else self.max_pressure))
        self.mean_duration_label.setText(
            "{} frames".format(0 if self.mean_duration == float("inf") else self.mean_duration))
        self.mean_surface_label.setText(
            "{} pixels".format(0 if self.mean_surface == float("inf") else self.mean_surface))

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width() / float(item_size.width()),
                    self.view.viewport().height() / float(item_size.height()))

        if abs(1 - ratio) > 0.1:
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)


class ContactView(QtGui.QGraphicsView):
    def __init__(self, contact_label, parent=None):
        super(ContactView, self).__init__(parent)
        self.contact_label = contact_label
        self.parent = parent

    def mouseDoubleClickEvent(self, event):
        pub.sendMessage("select_contact", contact_label=self.contact_label)