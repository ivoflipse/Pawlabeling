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

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ForceViewWidget(QWidget):
    def __init__(self, parent):
        super(ForceViewWidget, self).__init__(parent)
        self.label = QLabel("Force View")
        self.parent = parent

        self.left_front = PawView(self, label="Left Front")
        self.left_hind = PawView(self, label="Left Hind")
        self.right_front = PawView(self,label="Right Front")
        self.right_hind = PawView(self, label="Right Hind")

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

    # How do I tell which measurement we're at?
    def update_paws(self, paw_labels, paw_data, average_data):
        # Clear the paws, so we can draw new ones
        self.clear_paws()

        # Group all the data per paw
        data_array = defaultdict(list)
        for measurement_name, data_list in paw_data.items():
            for paw_label, data in zip(paw_labels[measurement_name].values(), data_list):
                if paw_label >= 0:
                    data_array[paw_label].append(data)

        # Do I need to cache information so I can use it later on? Like in predict_label?
        for paw_label, average_list in average_data.items():
            data = data_array[paw_label]
            widget = self.paws_list[paw_label]
            widget.update(data, average_list)

    def update_n_max(self, n_max):
        for paw_label, paw in list(self.paws_list.items()):
            paw.n_max = n_max

    def clear_paws(self):
        for paw_label, paw in list(self.paws_list.items()):
            paw.clear_paws()

class PawView(QWidget):
    def __init__(self, parent, label):
        super(PawView, self).__init__(parent)
        self.label = QLabel(label)
        self.parent = parent
        self.n_max = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

        self.dpi = 100
        self.fig = Figure((3.0, 2.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.canvas)
        self.main_layout.addStretch(1)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self, paw_data, average_data):
        self.axes.cla()
        for data in paw_data:
            x, y, z = data.shape
            force_over_time = np.sum(np.sum(data, axis=0), axis=0)
            self.axes.plot(force_over_time)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.canvas.draw()

    def change_frame(self, frame):
        self.vertical_line.set_xdata(frame)
        self.canvas.draw()

    def clear_paws(self):
        # Put the screen to black
        self.axes.cla()
        self.canvas.draw()
