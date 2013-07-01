from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
from view import View

import utility

class EntirePlateWidget(QWidget):
    def __init__(self, degree, size, parent = None):
        super(EntirePlateWidget, self).__init__(parent)
        self.parent = parent
        self.resize(size[0], size[1])
        self.layout = QVBoxLayout(self)

        self.scene = QGraphicsScene(self)
        self.view = View(self.scene, widget = self)
        self.layout.addWidget(self.view)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)
        self.view.centerOn(self.image)

        # This pen is used to draw the polygons
        self.pen = QPen(Qt.white)
        # I can also draw with a brush
        self.brush = QBrush(Qt.white)
        # A cache to store the polygons of the previous frame
        self.previouspolygons = []
        self.bounding_boxes = []
        self.gait_lines = []
        self.colors = [
                      QColor(Qt.darkCyan),
                      QColor(Qt.gray),
                      QColor(Qt.darkMagenta),
                      QColor(Qt.green),
                      QColor(Qt.red),
                      ]

        self.degree = degree

    def newMeasurement(self, measurement):
        # Update the measurement
        self.measurement = measurement
        self.height, self.width, self.numFrames = self.measurement.shape
        self.nmin = self.measurement.min()
        self.nmax = self.measurement.max()
        self.changeFrame(frame=0)

    def newPaws(self, paws):
        # Update the paws
        self.paws = paws
        self.draw_bounding_box()
        self.draw_gait_line()

    def changeFrame(self, frame):
        # Set the frame
        self.frame = frame
        # Slice out the data from the measurement
        self.data = self.measurement[:, :, self.frame].T
        # Update the pixmap
        self.self.image.setPixmap(utility.getQPixmap(self.data, self.degree, self.nmin, self.nmax))

    def draw_bounding_box(self):
        self.bboxpen = QPen(Qt.white)
        self.bboxpen.setWidth(3)
        # Remove the old ones and redraw
        for box in self.bounding_boxes:
            self.scene.removeItem(box)
        self.bounding_boxes = []
               
        # Container to map contours to colors        
        self.paw_colors = []

        for index, paw in enumerate(self.paws):
            if len(paw.frames) > 1:
                #color = self.colors[index % len(self.colors)]  # We'll default to white first
                color = QColor(Qt.white)
                self.bboxpen.setColor(color)
                polygon = QPolygonF([QPointF(paw.totalminx * self.degree, paw.totalminy * self.degree),
                                     QPointF(paw.totalmaxx * self.degree, paw.totalminy * self.degree),
                                     QPointF(paw.totalmaxx * self.degree, paw.totalmaxy * self.degree),
                                     QPointF(paw.totalminx * self.degree, paw.totalmaxy * self.degree)])

                self.paw_colors.append([paw. totalcentroid, paw.totalminx, paw.totalmaxx, paw.totalminy, paw.totalmaxy, color])
                self.bounding_boxes.append(self.scene.addPolygon(polygon, self.bboxpen))

    def draw_gait_line(self):
        self.gait_line_pen = QPen(Qt.white)
        self.gait_line_pen.setWidth(1)
        self.gait_line_pen.setColor(Qt.white)

        for line in self.gait_lines:
            self.scene.removeItem(line)
        self.gait_lines = []

        for index in range(1, len(self.paws)):
            prevPaw = self.paws[index-1]
            curPaw = self.paws[index]
            polygon = QPolygonF([QPointF(prevPaw.totalcentroid[0] * self.degree, prevPaw.totalcentroid[1] * self.degree),
                                 QPointF(curPaw.totalcentroid[0] * self.degree, curPaw.totalcentroid[1] * self.degree)])
            self.gait_lines.append(self.scene.addPolygon(polygon, self.gait_line_pen))





