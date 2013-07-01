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
        self.current_box = None
        self.gait_lines = []
        self.colors = [
                      QColor(Qt.green),
                      QColor(Qt.darkGreen),
                      QColor(Qt.red),
                      QColor(Qt.darkRed),
                      QColor(Qt.yellow),
                      ]

        self.degree = degree

    def newMeasurement(self, measurement):
        # Clear the bounding boxes + the line
        self.clear_bounding_box()
        self.clear_gait_line()
        # Update the measurement
        self.measurement = measurement
        self.height, self.width, self.numFrames = self.measurement.shape
        self.nmin = self.measurement.min()
        self.nmax = self.measurement.max()
        self.changeFrame(frame=-1)

    def newPaws(self, paws):
        # Update the paws
        self.paws = paws
        self.draw_bounding_box()
        self.draw_gait_line()

    def changeFrame(self, frame):
        # Set the frame
        self.frame = frame
        if frame == -1:
            self.data = self.measurement.max(axis=2).T
        else:
            # Slice out the data from the measurement
            self.data = self.measurement[:, :, self.frame].T
        # Update the pixmap
        self.image.setPixmap(utility.getQPixmap(self.data, self.degree, self.nmin, self.nmax))

    def clear_bounding_box(self):
        # Remove the old ones and redraw
        for box in self.bounding_boxes:
            self.scene.removeItem(box)
        self.bounding_boxes = []

    def clear_gait_line(self):
        # Remove the gait line
        for line in self.gait_lines:
            self.scene.removeItem(line)
        self.gait_lines = []

    def draw_bounding_box(self):
        self.bboxpen = QPen(Qt.white)
        self.bboxpen.setWidth(3)

        self.clear_bounding_box()
        for index, paw in enumerate(self.paws):
            if len(paw.frames) > 1:
                #color = self.colors[index % len(self.colors)]  # We'll default to white first
                polygon = QPolygonF([QPointF(paw.totalminx * self.degree, paw.totalminy * self.degree),
                                     QPointF(paw.totalmaxx * self.degree, paw.totalminy * self.degree),
                                     QPointF(paw.totalmaxx * self.degree, paw.totalmaxy * self.degree),
                                     QPointF(paw.totalminx * self.degree, paw.totalmaxy * self.degree)])

                self.bounding_boxes.append(self.scene.addPolygon(polygon, self.bboxpen))

    def update_bounding_box(self, index, paw_label):
        color = self.colors[paw_label]
        self.bboxpen = QPen(color)
        self.bboxpen.setWidth(3)

        if paw_label == -1:
            if self.current_box:
                self.scene.removeItem(self.current_box)
            self.bboxpen.setWidth(5)
        else:
            old_box = self.bounding_boxes[index]
            self.scene.removeItem(old_box)

        paw = self.paws[index]
        polygon = QPolygonF([QPointF(paw.totalminx * self.degree, paw.totalminy * self.degree),
                           QPointF(paw.totalmaxx * self.degree, paw.totalminy * self.degree),
                           QPointF(paw.totalmaxx * self.degree, paw.totalmaxy * self.degree),
                           QPointF(paw.totalminx * self.degree, paw.totalmaxy * self.degree)])

        if paw_label == -1:
            self.current_box = self.scene.addPolygon(polygon, self.bboxpen)
        else:
            self.bounding_boxes[index] = self.scene.addPolygon(polygon, self.bboxpen)


    def draw_gait_line(self):
        self.gait_line_pen = QPen(Qt.white)
        self.gait_line_pen.setWidth(1)
        self.gait_line_pen.setColor(Qt.white)

        self.clear_gait_line()

        for index in range(1, len(self.paws)):
            prevPaw = self.paws[index-1]
            curPaw = self.paws[index]
            polygon = QPolygonF([QPointF(prevPaw.totalcentroid[0] * self.degree, prevPaw.totalcentroid[1] * self.degree),
                                 QPointF(curPaw.totalcentroid[0] * self.degree, curPaw.totalcentroid[1] * self.degree)])
            self.gait_lines.append(self.scene.addPolygon(polygon, self.gait_line_pen))





