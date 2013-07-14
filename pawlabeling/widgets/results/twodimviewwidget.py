#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from collections import defaultdict

import numpy as np
from PySide.QtCore import *
from PySide.QtGui import *

from settings import configuration
from functions import utility, gui

class TwoDimViewWidget(QWidget):
    def __init__(self, parent, degree):
        super(TwoDimViewWidget, self).__init__(parent)
        self.label = QLabel("2D View")
        self.parent = parent
        self.degree = configuration.degree * 2

        self.left_front = PawView(self, self.degree, label="Left Front")
        self.left_hind = PawView(self, self.degree, label="Left Hind")
        self.right_front = PawView(self, self.degree, label="Right Front")
        self.right_hind = PawView(self, self.degree, label="Right Hind")

        self.paws_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
            }

        self.clear_paws()

        self.left_paws_layout = QVBoxLayout()
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(self.left_hind)
        self.right_paws_layout = QVBoxLayout()
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(self.right_hind)

        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.left_paws_layout)
        self.main_layout.addLayout(self.right_paws_layout)
        self.setLayout(self.main_layout)

    def clear_paws(self):
        for paw_label, paw in list(self.paws_list.items()):
            paw.clear_paws()

class PawView(QWidget):
    def __init__(self, parent, degree, label):
        super(PawView, self).__init__(parent)
        self.label = QLabel(label)
        self.parent = parent
        self.degree = degree
        self.n_max = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 15
        self.my = 15
        self.data = np.zeros((self.mx, self.my))
        self.data_list = []
        self.average_data_list = []

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setGeometry(0, 0, 100, 100)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self):
        self.image.setPixmap(utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table))

    def clear_paws(self):
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(np.zeros((self.mx, self.my)), self.degree, self.n_max, self.color_table))

