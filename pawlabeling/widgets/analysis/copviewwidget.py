import logging
import numpy as np
from PySide import QtGui, QtCore
from pawlabeling.functions import utility, calculations
from pawlabeling.settings import configuration
from pubsub import pub

logger = logging.getLogger("logger")

class CopViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(CopViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
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
        self.n_max = 0
        self.degree = configuration.interpolation_results
        self.mx = 15
        self.my = 15
        self.min_x = 0
        self.max_x = 15
        self.min_y = 0
        self.max_y = 15
        self.max_z = 0
        self.frame = -1
        self.active = False
        self.filtered = []
        self.outlier_toggle = False
        self.ratio = 1
        self.cop_x = np.zeros(15)
        self.cop_y = np.zeros(15)
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

        self.line_pen = QtGui.QPen(QtCore.Qt.white)
        self.line_pen.setWidth(2)

        self.dot_pen = QtGui.QPen(QtCore.Qt.black)
        self.dot_pen.setWidth(2)
        self.dot_brush = QtGui.QBrush(QtCore.Qt.white)

        self.cop_lines = []
        self.cop_ellipses = []

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
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
        #pub.subscribe(self.resizeEvent, "resize_event")

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
        self.max_z = np.max(z) + 1 # Added some padding here

        self.draw_frame()

    def draw_cop(self):
        # If we still have the default shape, don't bother
        if self.average_data.shape == (15, 15, 15):
            return

        # Remove all the previous ellipses if coming back from update_cop
        for item in self.cop_ellipses:
            self.scene.removeItem(item)
        self.cop_ellipses = []

        # This value determines how many points of the COP are being plotted.
        self.x = 15

        # Just calculate the COP over the average data
        average_data = np.rot90(np.rot90(self.average_data[self.min_x:self.max_x, self.min_y:self.max_y, :self.max_z]))
        # For some reason I can't do the slicing in the above call
        average_data = average_data[:,::-1,:]
        self.cop_x, self.cop_y = calculations.calculate_cop(average_data)

        # Create a strided index
        index = [x for x in range(0, self.max_z, int(self.max_z / self.x))]

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

        # Get the very last value
        x1, y1 = self.cop_x[-1], self.cop_y[-1]
        ellipse = self.scene.addEllipse(x1 * self.degree, y1 * self.degree, 5, 5, self.dot_pen, self.dot_brush)
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
        self.pixmap = utility.get_QPixmap(self.sliced_data, self.degree, self.n_max, self.color_table)
        self.image.setPixmap(self.pixmap)
        self.resizeEvent()

    def change_frame(self, frame):
        self.frame = frame
        # If we're not displaying the empty array
        if self.max_of_max.shape != (self.mx, self.my) and self.active:
            self.draw_frame()

    def clear_cached_values(self):
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

    def resizeEvent(self, event=None):
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

