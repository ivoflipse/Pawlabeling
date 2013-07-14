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


class ResultsWidget(QWidget):
    def __init__(self, parent):
        super(ResultsWidget, self).__init__(parent)

        self.two_dim_view_widget = TwoDimViewWidget(self, degree=4)
        self.pressure_widget = PressureWidget(self)
        self.force_widget = ForceWidget(self)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.two_dim_view_widget, "2D view")
        self.tab_widget.addTab(self.pressure_widget, "Pressure")
        self.tab_widget.addTab(self.force_widget, "Force")

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)


# I could just treat each of these classes as one widget, so each tab gets for of them
class TwoDimViewWidget(QWidget):
    def __init__(self, parent, degree):
        super(TwoDimViewWidget, self).__init__(parent)
        self.label = QLabel("2D View")
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

        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self):
        self.image.setPixmap(utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table))

    def clear_paws(self):
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(np.zeros((self.mx, self.my)), self.degree, self.n_max, self.color_table))


class PressureWidget(QWidget):
    def __init__(self, parent):
        super(PressureWidget, self).__init__(parent)
        self.label = QLabel("Pressure")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)

class ForceWidget(QWidget):
    def __init__(self, parent):
        super(ForceWidget, self).__init__(parent)
        self.label = QLabel("Force")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
