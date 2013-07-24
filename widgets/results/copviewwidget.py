from collections import defaultdict

import numpy as np
from PySide import QtGui, QtCore

from settings import configuration
from functions import utility, calculations

class CopViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(CopViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
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

    # How do I tell which measurement we're at?
    def update_paws(self, paw_labels, paw_data, average_data):
        # Clear the paws, so we can draw new ones
        self.clear_paws()
        max_length = 0

        # Group all the data per paw
        data_array = defaultdict(list)
        for measurement_name, data_list in paw_data.items():
            for paw_label, data in zip(paw_labels[measurement_name].values(), data_list):
                if paw_label >= 0:
                    data_array[paw_label].append(data)
                    # Get the max values for the plots
                    x, y, z = data.shape
                    if z > max_length:
                        max_length = z

        # Do I need to cache information so I can use it later on? Like in predict_label?
        for paw_label, average_list in average_data.items():
            data = data_array[paw_label]
            widget = self.paws_list[paw_label]
            widget.x = max_length
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

class PawView(QtGui.QWidget):
    def __init__(self, parent, label):
        super(PawView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.parent = parent
        self.n_max = 0
        self.degree = configuration.degree * 4
        self.mx = 15
        self.my = 15
        self.min_x = 0
        self.max_x = 15
        self.min_y = 0
        self.max_y = 15
        self.frame = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

        self.cop_lines = []
        self.cop_ellipses = []

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setGeometry(0, 0, 100, 100)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        self.main_layout.addStretch(1)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self, paw_data, average_data):
        self.frame = -1
        self.max_of_max = np.mean(average_data, axis=0)

        # The result of calculate_average_data = (number of paws, rows, colums, frames)
        # so mean axis=0 is mean over all paws
        self.average_data = np.mean(utility.calculate_average_data(paw_data), axis=0)
        x, y, z = np.nonzero(self.average_data)
        # Pray this never goes out of bounds
        self.min_x = np.min(x) - 2
        self.max_x = np.max(x) + 2
        self.min_y = np.min(y) - 2
        self.max_y = np.max(y) + 2

        self.draw_frame()
        self.draw_cop(paw_data)

    def draw_cop(self, paw_data):
        color = QtCore.Qt.white
        self.line_pen = QtGui.QPen(color)
        self.line_pen.setWidth(3)

        self.dot_pen = QtGui.QPen(QtCore.Qt.black)
        self.dot_pen.setWidth(2)
        self.dot_brush = QtGui.QBrush(QtCore.Qt.white)

        # This value determines how many points of the COP are being plotted.
        self.x = 15

        num_paws = len(paw_data)
        cop_xs = np.zeros((num_paws, self.x))
        cop_ys = np.zeros((num_paws, self.x))
        for index, data in enumerate(paw_data):
            # I first interpolated using the length, but then I switched to a default for now. Fix later
            x, y, z = data.shape
            # Reversing the left-right direction. I should really figure out where this is coming from
            cop_x, cop_y = calculations.calculate_cop(np.rot90(np.rot90(data[:,::-1,:])))
            cop_xs[index, :] = calculations.interpolate_time_series(cop_x, length=self.x)
            cop_ys[index, :] = calculations.interpolate_time_series(cop_y, length=self.x)

        average_cop_x = np.mean(cop_xs, axis=0)
        average_cop_y = np.mean(cop_ys, axis=0)
        # Initialize these values just in case
        x1, x2, y1, y2 = 0, 0, 0, 0

        for frame in range(len(average_cop_x)-1):
            x1 = average_cop_x[frame]
            x2 = average_cop_x[frame+1]
            y1 = average_cop_y[frame]
            y2 = average_cop_y[frame+1]

            line = QtCore.QLineF(QtCore.QPointF(x1 * self.degree, y1 * self.degree),
                                 QtCore.QPointF(x2 * self.degree, y2 * self.degree))

            self.cop_lines.append(self.scene.addLine(line, self.line_pen))
            self.cop_ellipses.append(self.scene.addEllipse(x1 * self.degree, y1 * self.degree,
                                                       5, 5, self.dot_pen, self.dot_brush))

        self.cop_ellipses.append(self.scene.addEllipse(x2 * self.degree, y2 * self.degree,
                                                    5, 5, self.dot_pen, self.dot_brush))

    def draw_frame(self):
        if self.frame == -1:
            self.sliced_data = self.max_of_max[self.min_x:self.max_x,self.min_y:self.max_y]
        else:
            self.sliced_data = self.average_data[self.min_x:self.max_x,self.min_y:self.max_y,self.frame]

        # Make sure the paws are facing upright
        self.sliced_data = np.rot90(np.rot90(self.sliced_data))
        self.sliced_data = self.sliced_data[:, ::-1]
        # Display the average data for the requested frame
        self.image.setPixmap(utility.get_QPixmap(self.sliced_data, self.degree, self.n_max, self.color_table))

    def change_frame(self, frame):
        self.frame = frame
        # If we're not displaying the empty array
        if self.max_of_max.shape != (self.mx, self.my):
            self.draw_frame()

    def clear_paws(self):
        self.sliced_data = np.zeros((self.mx, self.my))
        self.average_data = self.sliced_data
        self.max_of_max = self.sliced_data
        self.min_x, self.max_x, self.min_y, self.max_y = 0, self.mx, 0, self.my
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(np.zeros((self.mx, self.my)), self.degree, self.n_max, self.color_table))
        for point in self.cop_ellipses:
            self.scene.removeItem(point)
        self.cop_ellipses = []

        for cop in self.cop_lines:
            self.scene.removeItem(cop)
        self.cop_lines = []

