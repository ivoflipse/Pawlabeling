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

class PressureViewWidget(QWidget):
    def __init__(self, parent):
        super(PressureViewWidget, self).__init__(parent)
        self.label = QLabel("Pressure View")
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
        max_pressure = 0
        max_length = 0
        for measurement_name, data_list in paw_data.items():
            for paw_label, data in zip(paw_labels[measurement_name].values(), data_list):
                if paw_label >= 0:
                    data_array[paw_label].append(data)
                    # Get the max values for the plots
                    x, y, z = data.shape
                    if z > max_length:
                        max_length = z
                    max_val = np.max(np.sum(np.sum(data, axis=0), axis=0))
                    index = np.argmax(np.sum(np.sum(data, axis=0), axis=0))
                    pixel_counts = np.count_nonzero(data[:, :, index])
                    pressure = max_val / (pixel_counts * configuration.sensor_surface)
                    if pressure > max_pressure:
                        max_pressure = pressure

        # Do I need to cache information so I can use it later on? Like in predict_label?
        for paw_label, average_list in average_data.items():
            data = data_array[paw_label]
            widget = self.paws_list[paw_label]
            widget.x = max_length + 1
            widget.y = max_pressure * 1.2
            widget.update(data, average_list)

    def update_n_max(self, n_max):
        for paw_label, paw in list(self.paws_list.items()):
            paw.n_max = n_max

    def change_frame(self, frame):
        self.frame = frame
        for paw_label, paw in list(self.paws_list.items()):
            paw.change_frame(frame)

    def clear_paws(self):
        for paw_label, paw in list(self.paws_list.items()):
            paw.clear_paws()

class PawView(QWidget):
    def __init__(self, parent, label):
        super(PawView, self).__init__(parent)
        self.label = QLabel(label)
        self.parent = parent
        self.n_max = 0
        self.frame = 0
        self.x = 0
        self.y = 0
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
        pressure_over_time = np.zeros((len(paw_data), self.x))
        for index, data in enumerate(paw_data):
            x, y, z = data.shape
            force_over_time = np.sum(np.sum(data, axis=0), axis=0)
            pixel_count = np.array([np.count_nonzero(data[:, :, frame]) for frame in range(z)])
            pressure = []
            for force, num_pixels in zip(force_over_time, pixel_count):
                if num_pixels > 0:
                    pressure.append(force / (num_pixels*configuration.sensor_surface))  # Remember, sensors are small!
            pressure_over_time[index, :z] = pressure
            self.axes.plot(pressure_over_time[index, :])

        self.axes.plot(np.mean(pressure_over_time, axis=0), color="r", linewidth=3)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.axes.set_xlim([0, self.x])
        self.axes.set_ylim([0, self.y])
        self.canvas.draw()

    def change_frame(self, frame):
        self.frame = frame
        self.vertical_line.set_xdata(frame)
        self.canvas.draw()

    def clear_paws(self):
        # Put the screen to black
        self.axes.cla()
        self.canvas.draw()
