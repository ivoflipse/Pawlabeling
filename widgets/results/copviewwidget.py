from collections import defaultdict

import numpy as np
from PySide import QtGui, QtCore

from settings import configuration
from functions import utility, calculations

import logging
logger = logging.getLogger("logger")

class CopViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(CopViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
        self.parent = parent

        self.left_front = PawView(self, label="Left Front")
        self.left_hind = PawView(self, label="Left Hind")
        self.right_front = PawView(self, label="Right Front")
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
            # Skip updating if there's no data
            if len(data) == 0:
                logger.info("No data found for {}".format(configuration.paw_dict[paw_label]))
                continue
            # Filtering outliers makes no sense when there's only one value
            elif len(data) > 1:
                data = utility.filter_outliers(data)
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
        self.degree = configuration.interpolation_results
        self.mx = 15
        self.my = 15
        self.min_x = 0
        self.max_x = 15
        self.min_y = 0
        self.max_y = 15
        self.frame = 0
        self.ratio = 1
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

        self.cop_lines = []
        self.cop_ellipses = []

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        #self.view.setGeometry(0, 0, 100, 100)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self, paw_data, average_data):
        self.frame = -1
        self.max_of_max = np.mean(average_data, axis=0)

        # The result of calculate_average_data = (number of paws, rows, colums, frames)
        # so mean axis=0 is mean over all paws
        self.average_data = np.mean(utility.calculate_average_data(paw_data), axis=0)
        self.paw_data = paw_data

        x, y, z = np.nonzero(self.average_data)
        # Pray this never goes out of bounds
        self.min_x = np.min(x) - 2
        self.max_x = np.max(x) + 2
        self.min_y = np.min(y) - 2
        self.max_y = np.max(y) + 2
        self.max_z = np.max(z)

        self.draw_frame()

    def draw_cop(self):
        # Remove all the previous ellipses if coming back from update_cop
        for item in self.cop_ellipses:
            self.scene.removeItem(item)
        self.cop_ellipses = []

        color = QtCore.Qt.white
        self.line_pen = QtGui.QPen(color)
        self.line_pen.setWidth(2)

        self.dot_pen = QtGui.QPen(QtCore.Qt.black)
        self.dot_pen.setWidth(2)
        self.dot_brush = QtGui.QBrush(QtCore.Qt.white)

        # This value determines how many points of the COP are being plotted.
        self.x = 15

        # Just calculate the COP over the average data
        average_data = np.rot90(np.rot90(self.average_data[self.min_x:self.max_x, self.min_y:self.max_y, :self.max_z]))
        # For some reason I can't do the slicing in the above call
        average_data = average_data[:,::-1,:]
        self.cop_x, self.cop_y = calculations.calculate_cop(average_data, version="numpy")

        # Create a strided index
        index = [x for x in range(0, self.max_z, int(self.max_z / self.x))]

        x2, y2 = 0, 0

        for frame in range(len(self.cop_x)-1):
            x1 = self.cop_x[frame]
            x2 = self.cop_x[frame + 1]
            y1 = self.cop_y[frame]
            y2 = self.cop_y[frame + 1]

            line = QtCore.QLineF(QtCore.QPointF(x1 * self.degree, y1 * self.degree),
                                 QtCore.QPointF(x2 * self.degree, y2 * self.degree))

            line = self.scene.addLine(line, self.line_pen)
            line.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
            self.cop_lines.append(line)

            # We only plot a couple of the ellipses
            if frame in index:
                ellipse = self.scene.addEllipse(x1 * self.degree, y1 * self.degree, 5, 5, self.dot_pen, self.dot_brush)
                ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
                self.cop_ellipses.append(ellipse)

        ellipse = self.scene.addEllipse(x2 * self.degree, y2 * self.degree, 5, 5, self.dot_pen, self.dot_brush)
        ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
        self.cop_ellipses.append(ellipse)

    def update_cop(self):
        # Remove all the previous ellipses
        for item in self.cop_ellipses:
            self.scene.removeItem(item)
        self.cop_ellipses = []

        # Only draw if the frame is actually available
        if self.frame < self.cop_x.shape[0]:
            cop_x = self.cop_x[self.frame]
            cop_y = self.cop_y[self.frame]
            ellipse = self.scene.addEllipse(cop_x * self.degree, cop_y * self.degree, 5, 5, self.dot_pen, self.dot_brush)
            ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
            self.cop_ellipses.append(ellipse)

    def draw_frame(self):
        if self.frame == -1:
            self.sliced_data = self.max_of_max[self.min_x:self.max_x, self.min_y:self.max_y]
            self.draw_cop()
        else:
            self.sliced_data = self.average_data[self.min_x:self.max_x,self.min_y:self.max_y, self.frame]
            self.update_cop()

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
        self.average_data = np.zeros((self.mx, self.my, 15))
        self.max_of_max = self.sliced_data
        self.paw_data = []
        self.min_x, self.max_x, self.min_y, self.max_y = 0, self.mx, 0, self.my
        # Put the screen to black
        self.image.setPixmap(
            utility.get_QPixmap(np.zeros((self.mx, self.my)), self.degree, self.n_max, self.color_table))
        for point in self.cop_ellipses:
            self.scene.removeItem(point)
        self.cop_ellipses = []

        for cop in self.cop_lines:
            self.scene.removeItem(cop)
        self.cop_lines = []

    def resizeEvent(self, event):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width() / float(item_size.width()),
                    self.view.viewport().height() / float(item_size.height()))

        if abs(1 - ratio) > 0.1:
            self.ratio = self.ratio * ratio
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            for item in self.cop_ellipses:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            for item in self.cop_lines:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)