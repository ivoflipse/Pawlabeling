import logging
import numpy as np
from PySide import QtGui
from pubsub import pub
from pawlabeling.functions import utility
from pawlabeling.settings import settings

logger = logging.getLogger("logger")

class TwoDimViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(TwoDimViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("2D View")
        self.parent = parent

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
        for contact_label, widget in self.contacts_list.items():
            if self.active:
                widget.change_frame(frame)
            else:
                widget.frame = frame

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            for contact_label, widget in self.contacts_list.items():
                widget.draw()

class ContactView(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(ContactView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.contact_label = contact_label
        self.parent = parent
        self.settings = settings.settings
        self.degree = self.settings.interpolation_results()
        self.n_max = 0
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
        self.filtered = []
        self.outlier_toggle = False
        self.data = np.zeros((self.mx, self.my))
        self.average_data = np.zeros((self.mx, self.my, 1))
        self.max_of_max = self.data.copy()

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

        # TODO I might want to (un)subscribe these
        pub.subscribe(self.update_n_max, "update_n_max")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.filter_outliers, "filter_outliers")
        pub.subscribe(self.update_average, "update_average")

    def update_average(self, average_data):
        if self.contact_label in average_data:
            self.average_data = average_data[self.contact_label]
            self.max_of_max = self.average_data.max(axis=2)
            self.change_frame(frame=-1)

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle

    def update_n_max(self, n_max):
        self.n_max = n_max
        self.draw()

    def draw(self):
        if self.frame == -1:
            self.data = self.max_of_max
        else:
            self.data = self.average_data[:, :, self.frame]

        # Make sure the contacts are facing upright
        self.data = np.rot90(np.rot90(self.data))
        self.data = self.data[:, ::-1]
        # Display the average measurement_data for the requested frame
        self.image.setPixmap(utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table))
        self.resizeEvent()

    def change_frame(self, frame):
        self.frame = frame
        # If we're not displaying the empty array
        if self.max_of_max.shape != (self.mx, self.my):
            self.draw()

    def clear_cached_values(self):
        self.data = np.zeros((self.mx, self.my))
        self.average_data = np.zeros((self.mx, self.my, 15))
        self.max_of_max = self.data[:]
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table))

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width()/float(item_size.width()),
                    self.view.viewport().height()/float(item_size.height()))

        if abs(1-ratio) > 0.1:
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)