from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
from view import View

import utility

class Widget(QWidget):
    def __init__(self, filename, measurement, paws, degree, size, parent = None):
        super(Widget, self).__init__(parent)
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
        self.colors = [
                      QColor(Qt.darkCyan),
                      QColor(Qt.gray),
                      QColor(Qt.darkMagenta),
                      QColor(Qt.green),
                      QColor(Qt.red),
                      ]

        self.measurement = measurement
        self.paws = paws
        
        # Get the number of Frames for the slider
        self.height, self.width, self.numFrames = self.measurement.shape
        
        self.degree = degree
        self.delta = 0
        
        # These are the min and max values of the entire measurement
        self.nmin = self.measurement.min()
        self.nmax = self.measurement.max()
        
        # Draw the bounding boxes for all the paws that have been found so far                                                     
        self.draw_bounding_box()
    
    def updateSlice(self):
        # Pass the message to the parent
        self.parent.updateDialog()
        
    def newMeasurement(self, measurement, paws):
        # Update the measurement
        self.measurement = measurement
        # Update the paws
        self.paws = paws
        # Set the frame to zero
        self.changeFrame(frame = 0)
        self.draw_bounding_box()

    def getData(self, frame):      
        # Set the frame
        self.frame = frame
        # Slice out the data from the measurement
        self.data = self.measurement[:, :, self.frame].T    
        
    def changeFrame(self, frame):
        self.frame = frame
        self.getData(self.frame)
        self.update_pixmap()
  
    def update_pixmap(self):
        # Set the pixmap with the data
        self.image.setPixmap(utility.getQPixmap(self.data, self.degree, self.nmin, self.nmax))  
        # Draw the contours
        self.draw_contours()
    
    def draw_bounding_box(self):
        self.bboxpen = QPen(Qt.white)
        self.bboxpen.setWidth(5)
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
                               
    def draw_contours(self):
        # Loop through the polygons of the previous frame and delete them
        for polygon in self.previouspolygons:
            self.scene.removeItem(polygon)
        
        self.previouspolygons = []
        
        # Loop through all the paws
        for index, paw in enumerate(self.paws):
            # Check if there are any contours for the given frame
            if self.frame in paw.contourList:
                for contour in paw.contourList[self.frame]:
                    polygon = utility.contourToPolygon(contour, self.degree)
                    color = self.colors[index % len(self.colors)]
                    self.pen.setColor(color)
                    self.pen.setWidth(1)
                    # Set the brush color to the same color as the pen, but transparent
                    brush_color = QColor(color)
                    brush_color.setAlpha(78)
                    self.brush.setColor(color)
                    polygon = self.scene.addPolygon(polygon, self.pen, self.brush)
                    # Store it so it can be deleted in the next frame
                    self.previouspolygons.append(polygon)     


