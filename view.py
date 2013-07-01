from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np

class View(QGraphicsView):
    def __init__(self, parent, widget):
        super(View, self).__init__(parent)
        self.parent = parent
        self.widget = widget

        self.select = True
        self.connect(self, SIGNAL("slice_paws"), self.setSelection)
        # Initialize the coordinates
        self.pressCoords = QPointF(0, 0)
        self.releaseCoords = QPointF(0, 0)
        self.raw_slice = []
        
        self.pen = QPen()
        self.pen.setStyle(Qt.DashDotLine)
        self.pen.setWidth(3)
        self.pen.setColor(Qt.red)        
        
        self.draw_rect = None        
        
        #self.connect(self.setSelection, SIGNAL("sliced_data"), parent.draw_selection)
        
    
    def resizeEvent(self, event):
        self.update()
        
    def setSelection(self):
        """
        This function is/was connected to a button on the toolbar, so I could set whether I wanted to be able to select a 
        rectangle or not. Now its just annoying I have to do extra work, so I'm dropping it for now. Its enabled by default.
        Instead this function will turn it off, just to mess with people! 
        """
        if self.select:
            self.select = False
        else:
            self.select = True
        
    def drawRectangle(self):
        # Send a signal with the coordinates
        if self.pressCoords != self.releaseCoords:
            print "Draw"
            if self.draw_rect:
                self.parent.removeItem(self.draw_rect)
            self.pressCoords = self.mapToScene(self.pressCoords.toPoint())
            self.releaseCoords = self.mapToScene(self.releaseCoords.toPoint())
            # Change them into a QPolygon
            x1 = self.pressCoords.x()
            y1 = self.pressCoords.y()
            x2 = self.releaseCoords.x()
            y2 = self.releaseCoords.y()
            self.slice = QPolygonF([QPointF(x1, y1), QPointF(x2, y1),
                                   QPointF(x2, y2), QPointF(x1, y2)])
            # Make sure x1 and y1 are always the lowest values
            x1, x2 = min([x1, x2]), max([x1, x2])
            y1, y2 = min([y1, y2]), max([y1, y2])
            self.raw_slice = [x1, y1, x2, y2]
            self.draw_rect = self.parent.addPolygon(self.slice, self.pen)
            # Send a signal back up the foodchain
            self.widget.updateSlice()
        
        
    def mousePressEvent(self, event):
        if self.select:
            if event.button() == Qt.LeftButton:      
                self.leftClick = True     
                self.pressCoords = event.posF()
                                  
    def mouseReleaseEvent(self, event):
        if self.select:
            self.leftClick = False  
            self.releaseCoords = event.posF()
            self.drawRectangle()
