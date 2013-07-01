from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np

class DialogView(QGraphicsView):    
    def __init__(self, parent, degree, coords, size):
        super(DialogView, self).__init__(parent)
        #self.resize(size[0], size[1])
        self.parent = parent
        self.degree = degree
        self.x1, self.y1, self.x2, self.y2 = coords
        self.select = True
        # Initialize the coordinates
        self.pressCoords = QPointF(0, 0)
        self.releaseCoords = QPointF(0, 0)
        self.raw_slice = []
        
        self.pen = QPen()
        self.pen.setWidth(3)
        self.pen.setColor(Qt.white)   
        
        color = QColor(Qt.white).setAlpha(75)
        self.brush = QBrush(color)
             
         # These are needed to draw a freehand shape
        self.pressCoords = QPointF(0, 0)
        self.releaseCoords = QPointF(0, 0)
        self.trackingCoords = []
        self.trackingPolygon = []
        self.leftClick = False
        self.setMouseTracking(True)
    
    def updateCoords(self, coords):
        self.x1, self.y1, self.x2, self.y2 = coords
        # Reset the tracking coords
        for line in self.trackingCoords:
            self.parent.removeItem(line)
        self.trackingCoords = []
        self.trackingPolygon = []
    
    def resizeEvent(self, event):
        #print event.size(), event.oldSize()
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  
            # Erase the polygon before starting
            for line in self.trackingCoords:
                self.parent.removeItem(line)
            self.trackingCoords = []
            self.trackingPolygon = []
            
            self.leftClick = True
            self.pressCoords = event.posF()
            self.previousCoords = event.posF()
                
    def mouseMoveEvent(self, event):
        # If its toggled on, track it
        if self.leftClick:
            self.currentCoords = event.posF()
            self.drawPolygon()
                                  
    def mouseReleaseEvent(self, event):
        self.leftClick = False  

        
    def drawPolygon(self):
        previousCoords = self.mapToScene(self.previousCoords.toPoint())
        currentCoords = self.mapToScene(self.currentCoords.toPoint())
        x1 = previousCoords.x()
        y1 = previousCoords.y()
        x2 = currentCoords.x()
        y2 = currentCoords.y()
        
        line = QPolygonF([QPointF(x1, y1), QPointF(x2, y2)])
        line = self.parent.addPolygon(line, self.pen, self.brush)
        self.trackingCoords.append(line)
        self.previousCoords = self.currentCoords
        
        # Store the raw x, y coordinates, so I can draw an OpenCV polygon
        self.trackingPolygon.append([[(previousCoords.x() / self.degree) + self.x1, (previousCoords.y() / self.degree) + self.y1]])
