import logging
from collections import defaultdict
import numpy as np
from PySide import QtGui
from pubsub import pub
from ...functions import utility
from ...settings import settings
from ...models import model


class TwoDimViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(TwoDimViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("2D View")
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
        self.settings = settings.settings
        self.degree = self.settings.interpolation_results()
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 1
        self.my = 1
        self.min_x = 0
        self.max_x = self.mx
        self.min_y = 0
        self.max_y = self.my
        self.max_z = 0
        self.frame = -1
        self.length = 0
        self.outlier_toggle = False
        self.average_toggle = False
        self.data = np.zeros((self.mx, self.my))

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        #self.view.setGeometry(0, 0, 100, 100)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        height = self.settings.contacts_widget_height()
        self.setMinimumHeight(height)
        self.setLayout(self.main_layout)

        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.filter_outliers, "filter_outliers")
        pub.subscribe(self.update_average, "update_average")
        pub.subscribe(self.update_contact, "put_contact")
        pub.subscribe(self.show_average_results, "show_average_results")

    def show_average_results(self, toggle):
        self.average_toggle = toggle
        self.clear_cached_values()
        if self.parent.active:
            self.change_frame(frame=-1)

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        self.clear_cached_values()
        if self.parent.active:
            self.change_frame(frame=-1)

    # TODO I'm not sure I want this state to even be in this widget
    def update_average(self):
        if self.contact_label in self.model.average_data:
            self.clear_cached_values()
            if self.parent.active:
                self.change_frame(frame=-1)

    def update_contact(self):
        if self.contact_label == self.model.contact.contact_label:
            self.clear_cached_values()
            if self.parent.active:
                self.change_frame(frame=-1)

    def get_data(self):
        if self.average_toggle:
            if self.frame == -1:
                self.data = self.model.average_data[self.contact_label].max(axis=2)
            else:
                self.data = self.model.average_data[self.contact_label][:, :, self.frame]
            self.length = self.model.average_data[self.contact_label].shape[2]
        else:
            if self.frame == -1:
                self.data = self.model.selected_contacts[self.contact_label].data.max(axis=2)
            else:
                self.data = self.model.selected_contacts[self.contact_label].data[:, :, self.frame]

            # Add padding, just like the average has
            self.data = np.pad(self.data, 2, mode="constant", constant_values=0)
            self.length = self.model.selected_contacts[self.contact_label].data.shape[2]

    def draw(self):
        self.get_data()

        # Make sure the contacts are facing upright
        self.data = np.rot90(np.rot90(self.data))
        self.data = self.data[:, ::-1]
        # Display the average measurement_data for the requested frame
        self.image.setPixmap(utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table))
        self.resizeEvent()

    def change_frame(self, frame):
        self.frame = frame
        # If we're not displaying the empty array
        if (self.frame < self.length and
                    self.contact_label in self.model.average_data and
                    self.contact_label in self.model.selected_contacts):
            self.draw()

    def clear_cached_values(self):
        self.frame = -1
        self.data = np.zeros((self.mx, self.my))
        # Put the screen to black
        self.image.setPixmap(utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table))

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width() / float(item_size.width()),
                    self.view.viewport().height() / float(item_size.height()))

        if abs(1 - ratio) > 0.1:
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)