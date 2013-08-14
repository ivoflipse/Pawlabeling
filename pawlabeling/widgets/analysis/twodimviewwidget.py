import logging

import numpy as np
from PySide import QtGui
from pawlabeling.functions import utility

from pawlabeling.settings import configuration
from pawlabeling.functions.pubsub import pub

logger = logging.getLogger("logger")

class TwoDimViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(TwoDimViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("2D View")
        self.parent = parent

        self.left_front = PawView(self, label="Left Front", paw_label=0)
        self.left_hind = PawView(self, label="Left Hind", paw_label=1)
        self.right_front = PawView(self, label="Right Front", paw_label=2)
        self.right_hind = PawView(self, label="Right Hind", paw_label=3)

        self.paws_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
            }

        self.left_paws_layout = QtGui.QVBoxLayout()
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(self.left_hind)
        self.right_paws_layout = QtGui.QVBoxLayout()
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_paws_layout)
        self.main_layout.addLayout(self.right_paws_layout)
        self.setLayout(self.main_layout)

class PawView(QtGui.QWidget):
    def __init__(self, parent, label, paw_label):
        super(PawView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.paw_label = paw_label
        self.parent = parent
        self.degree = configuration.interpolation_results
        self.n_max = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 15
        self.my = 15
        self.min_x = 0
        self.max_x = self.mx
        self.min_y = 0
        self.max_y = self.my
        self.frame = -1
        self.active = False
        self.filtered = []
        self.outlier_toggle = False
        self.data = np.zeros((self.mx, self.my))
        self.max_of_max = self.data.copy()
        self.sliced_data = self.data.copy()
        self.data_list = []
        self.average_data_list = []

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
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

        pub.subscribe(self.update_n_max, "update_n_max")
        pub.subscribe(self.change_frame, "analysis.change_frame")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.update, "analysis_results")
        pub.subscribe(self.check_active, "active_widget")
        pub.subscribe(self.filter_outliers, "filter_outliers")

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        #self.draw_frame()

    def check_active(self, widget):
        self.active = False
        # Check if I'm the active widget
        if self.parent == widget:
            self.active = True
            self.draw_frame()

    def update_n_max(self, n_max):
        self.n_max = n_max

    def update(self, paws, average_data, results, max_results):
        if self.paw_label not in average_data:
            return

        self.average_data = np.mean(average_data[self.paw_label], axis=0)
        self.max_of_max = np.max(self.average_data, axis=2)
        self.filtered = results[self.paw_label]["filtered"]

        x, y, z = np.nonzero(self.average_data)
        # Pray this never goes out of bounds
        self.min_x = np.min(x) - 2
        self.max_x = np.max(x) + 2
        self.min_y = np.min(y) - 2
        self.max_y = np.max(y) + 2
        self.max_z = np.max(z)

        self.draw_frame()

    def draw_frame(self):
        if self.frame == -1:
            self.sliced_data = self.max_of_max[self.min_x:self.max_x,self.min_y:self.max_y]
        else:
            self.sliced_data = self.average_data[self.min_x:self.max_x,self.min_y:self.max_y, self.frame]

        # Make sure the paws are facing upright
        self.sliced_data = np.rot90(np.rot90(self.sliced_data))
        self.sliced_data = self.sliced_data[:, ::-1]

        # Display the average data for the requested frame
        self.image.setPixmap(utility.get_QPixmap(self.sliced_data, self.degree, self.n_max, self.color_table))
        self.resizeEvent()

    def change_frame(self, frame):
        self.frame = frame
        # If we're not displaying the empty array
        if (self.max_of_max.shape != (self.mx, self.my) or self.max_z < self.frame) and self.active:
            self.draw_frame()

    def clear_cached_values(self):
        self.sliced_data = np.zeros((self.mx, self.my))
        self.average_data = np.zeros((self.mx, self.my, 15))
        self.max_of_max = self.sliced_data
        self.min_x, self.max_x, self.min_y, self.max_y = 0, self.mx, 0, self.my
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(np.zeros((self.mx, self.my)), self.degree, self.n_max, self.color_table))

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width()/float(item_size.width()),
                    self.view.viewport().height()/float(item_size.height()))

        if abs(1-ratio) > 0.1:
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)