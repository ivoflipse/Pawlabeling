# -*- coding: utf-8 -*-
"""
Created on Tue Aug 07 11:35:37 2012

@author: Ivo
"""

import cv2
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np

# This imports some functions that are being shared among classes
import utility
from dialogview import DialogView

from matplotlib import use, rcParams
use('Qt4Agg')
rcParams['backend.qt4']='PyQt4'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PopupWidget(QWidget):
    def __init__(self, measurement, coords, paws, degree, dilation, erosion, size, parent=None):
        super(PopupWidget, self).__init__(parent)
        self.resize(size[0], size[1])
        self.layout = QHBoxLayout()
        self.mainLayout = QVBoxLayout(self)

        # Assign some constants and pass along variables
        self.measurement = measurement
        self.x1, self.y1, self.x2, self.y2 = coords
        self.slice_data = self.measurement[self.x1:self.x2 + 1, self.y1:self.y2 + 1, :]
        # Get the number of Frames for the slider
        self.height, self.width, self.numFrames = self.slice_data.shape
        # Increase the degree to zoom in
        self.degree = degree #* 6 # This is very large!
        # These are the min and max values of the entire measurement
        self.nmin = self.measurement.min()
        self.nmax = self.measurement.max()
        self.paws = paws

        # Calculate which contours are visible
        self.checkVisibleContours()
        # Create a list to display all visible contacts        
        self.contactList = QListWidget(self)
        # This add all the paws to the contactList and creates a dictionary with the paws
        self.fillContactList(paws)
        self.layout.addWidget(self.contactList)

        self.scene = QGraphicsScene(self)
        self.view = DialogView(self.scene, self.degree, coords, size)
        self.mainLayout.addWidget(self.view, 0)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)
        self.view.centerOn(self.image)

        self.dpi = 100
        self.fig = Figure((3.0, 2.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.layout.addWidget(self.canvas)

        self.dilation_iterations = dilation
        self.erosion_iterations = erosion
        self.euclidean_distance = 25

        # This pen is used to draw the polygons
        self.pen = QPen(Qt.white)
        self.pen.setWidth(5)
        # I can also draw with a brush
        brushColor = QColor(Qt.white).setAlpha(70)
        self.brush = QBrush(brushColor)
        # A cache to store the polygons of the previous frame
        self.previouspolygons = []
        self.bounding_boxes = []
        self.colors = [
            #QColor(255, 222, 173),
            QColor(Qt.darkCyan),
            QColor(Qt.gray),
            QColor(Qt.darkMagenta),
            QColor(Qt.green),
            QColor(Qt.red),
        ]

        self.mainLayout.addLayout(self.layout)
        self.setLayout(self.mainLayout)

        # Initialize a colortable
        self.frame = 0
        self.updateSlice(coords)
        self.changeFrame(self.frame)
        self.bounding_boxes = []
        self.contactList.itemActivated.connect(self.draw_bounding_box)

    def resizeEvent(self, event):
        #print event.size(), event.oldSize()
        self.update()

    def fillContactList(self, paws):
        # Clear anything in the list
        self.contactList.clear()
        self.paws = paws
        item = None
        for index, paw in enumerate(self.paws):
            # Check if the paw is visible, else we don't want to list it
            if index in self.visibleContours:
                item = QListWidgetItem("Contact %s" % index)
                self.contactList.addItem(item)

        # Set the last item as the current item
        self.contactList.setCurrentItem(item)

    def sum_pressure(self):
        # Clear anything on the axes
        self.axes.cla()
        self.pressure = []
        for frame in range(self.numFrames):
            self.pressure.append(self.slice_data[:, :, frame].sum())
        self.pressure = np.array(self.pressure)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.axes.plot(self.pressure)

    def changeFrame(self, frame):
    # Set the frame
        self.frame = frame
        # Draw the new data
        self.update_pixmap()

    def newMeasurement(self, measurement, paws, coords):
        # Update the measurement
        self.measurement = measurement
        # Update the paw list
        self.paws = paws
        # Update the slice data
        self.updateSlice(coords)
        # Make sure everything updates
        self.changeFrame(self.frame)
        # Update the contactList
        self.fillContactList(self.paws) # Look out if this gets outdated!

    def checkVisibleContours(self):
        # Set which contours are visible
        self.visibleContours = set()
        # Loop through all the paws
        for index, paw in enumerate(self.paws):
            # Check if there are any contours for the given frame
            for frame in paw.contourList.keys():
                for contour in paw.contourList[frame]:
                    # Check if the contour is within the current slice or not
                    if self.contourInSlice(contour):
                        self.visibleContours.add(index)


    def updateSlice(self, coords):
        # Update the slice coords
        self.x1, self.y1, self.x2, self.y2 = coords
        self.view.updateCoords(coords)
        # Update the slice data
        self.slice_data = self.measurement[self.x1:self.x2 + 1, self.y1:self.y2 + 1, :]
        # Get the number of Frames for the slider
        self.height, self.width, self.numFrames = self.slice_data.shape
        # Update the pressure
        self.sum_pressure()
        # Calculate which contours are visible
        self.checkVisibleContours()
        # Update the list of visible contacts
        self.fillContactList(self.paws)
        # If there are any contacts
        if self.contactList.currentItem():
            # Draw the bounding boxes
            self.draw_bounding_box()

    def update_pixmap(self):
        # Create a pixmap
        qpixmap = utility.getQPixmap(self.slice_data[:, :, self.frame].T, self.degree, self.nmin, self.nmax)
        # Set the pixmap
        self.image.setPixmap(qpixmap)
        # Draw the contours
        self.draw_contours()
        # Draw a line based on where we are
        self.vertical_line.set_xdata(self.frame)
        self.canvas.draw()

    def draw_contours(self):
        # Loop through the polygons of the previous frame and delete them
        for polygon in self.previouspolygons:
            self.scene.removeItem(polygon)
            # Use a thicker pen
        self.pen.setWidth(5)
        self.previouspolygons = []

        # Also draw the contour of unassigned things
        contours = utility.findContours(self.measurement[:, :, self.frame].T)
        for contour in contours:
            polygon = utility.contourToPolygon(contour, self.degree, offsetx=self.x1, offsety=self.y1)
            color = Qt.white
            self.pen.setColor(color)
            self.pen.setWidth(3)
            polygon = self.scene.addPolygon(polygon, self.pen)
            self.previouspolygons.append(polygon)


            # Loop through all the paws
        for index, paw in enumerate(self.paws):
            # Check if the contour is within the current slice or not
            if index in self.visibleContours:
                # Check if there are any contours for the given frame
                if self.frame in paw.contourList:
                    for contour in paw.contourList[self.frame]:
                        polygon = utility.contourToPolygon(contour, self.degree, offsetx=self.x1, offsety=self.y1)
                        color = self.colors[index % len(self.colors)]
                        self.pen.setColor(color)
                        self.pen.setWidth(3)
                        brush_color = QColor(color)
                        brush_color.setAlpha(78)
                        self.brush.setColor(brush_color)
                        polygon = self.scene.addPolygon(polygon, self.pen, self.brush)
                        # Store it so it can be deleted in the next frame
                        self.previouspolygons.append(polygon)


    def contourInSlice(self, contour):
        # Check if the contour is within the boundaries of the slice
        xs, ys = utility.contourToLines(contour)
        minx = min(xs)
        maxx = max(xs)
        miny = min(ys)
        maxy = max(ys)
        if (self.x1 < minx < self.x2) and (self.y1 < miny < self.y2):
            return True
        return False


    def draw_bounding_box(self):
        """
        This function uses the index from the listwidget that belongs to a paw
        With the index we can get the paw from self.paws and get its appropriate color
        """
        self.bboxpen = QPen(Qt.white)
        # Remove the old ones and redraw
        for box in self.bounding_boxes:
            self.scene.removeItem(box)
        self.bounding_boxes = []

        currentItem = self.contactList.currentItem().text()
        # Get the contact index from the name
        index = int(currentItem.split(" ")[-1])
        self.currentIndex = index

        # Container to map contours to colors    
        paw = self.paws[index]
        color = self.colors[index % len(self.colors)]
        self.bboxpen.setColor(color)
        self.bboxpen.setWidth(1)
        # Subtract the offset of the pop up
        minx = paw.totalminx - self.x1
        maxx = paw.totalmaxx - self.x1
        miny = paw.totalminy - self.y1
        maxy = paw.totalmaxy - self.y1
        polygon = QPolygonF([QPointF(minx * self.degree, miny * self.degree),
                             QPointF(maxx * self.degree, miny * self.degree),
                             QPointF(maxx * self.degree, maxy * self.degree),
                             QPointF(minx * self.degree, maxy * self.degree)
        ])

        self.bounding_boxes.append(self.scene.addPolygon(polygon, self.bboxpen))

    def updateContourList(self):
        # Check if a paw is selected
        if not hasattr(self, "currentIndex"):
            print "First select a contact!"
            return
            # Make sure its closed by ending with the first element
        #        self.view.trackingPolygon.append(self.view.trackingPolygon[-1])
        # Show me the slice
        self.trackingPolygon = np.array(self.view.trackingPolygon, np.float32)

        # Take the data and find contours within the current frame
        contours = utility.findContours(self.measurement[:, :, self.frame].T)
        # Clear the contourList for that frame
        self.paws[self.currentIndex].contourList[self.frame] = []
        for contour in contours:
            # Iterate until we've found a match
            match = False
            # Check if the contour is within the tracking polygon
            for point in contour:
                coords = (point[0][0], point[0][1])
                if cv2.pointPolygonTest(self.trackingPolygon, coords, 0) > -1.0:
                    match = True
            if match:
                # Make sure its deleted from all the other paws
                self.deleteContour(contour)
                # Add the contour to the contourList
                self.paws[self.currentIndex].contourList[self.frame].append(contour)

        # When we're done, refresh the drawing of the pop up
        self.update_pixmap()
        print "Updated with %s contours" % (len(self.paws[self.currentIndex].contourList[self.frame]))

    # def createContact(self):
    #     print "Create Contact"
    #     # Check if some area has been selected
    #     if hasattr(self.view, "trackingPolygon"):
    #     # Show me the slice
    #         self.trackingPolygon = np.array(self.view.trackingPolygon, np.float32)
    #
    #         # Take the data and find contours within the current frame
    #         contours = utility.findContours(self.measurement[:, :, self.frame].T)
    #         # Check if there are any contours
    #         if not contours:
    #             return
    #
    #         matched_contours = []
    #         for contour in contours:
    #             # Iterate until we've found a match
    #             match = False
    #             # Check if the contour is within the tracking polygon
    #             for point in contour:
    #                 coords = (point[0][0], point[0][1])
    #                 if cv2.pointPolygonTest(self.trackingPolygon, coords, 0) > -1.0:
    #                     match = True
    #             if match:
    #                 matched_contours.append(contour)
    #
    #         # Check if we had any matches
    #         if not matched_contours:
    #             return
    #
    #         # Create a new contour object
    #         new_contour = contourtracker.Contour(matched_contours[0], self.frame, self.measurement)
    #         # Add the remaining contours if any
    #         for contour in matched_contours:
    #             new_contour.addContour(contour, self.frame)
    #             # Remove any duplicates
    #         new_contour.dedupeContours()
    #         # Calculate the bounding box
    #         new_contour.updateBoundingBox()
    #         # Add the contour to the list of contacts/paws
    #         self.paws.append(new_contour)
    #
    #         # Update the contactList
    #     #            self.fillContactList(self.paws)
    #     else:
    #         print "Please select an area that contains contours"


    def deleteContour(self, deleteContour):
        for paw in self.paws:
            # Check if the paw has any contours for that frame
            if self.frame in paw.contourList:
                deleteList = set()
                # If so, loop through them
                for index, contour in enumerate(paw.contourList[self.frame]):
                    # If the contour is visible
                    if index in self.visibleContours:
                        # If either contour has a length of 1
                        # How is this any different from the other check?
                        if len(deleteContour) == 1 or len(contour) == 1:
                            if deleteContour[0][0][0] == contour[0][0][0] and deleteContour[0][0][1] == contour[0][0][
                                                                                                        1] and len(
                                deleteContour) == len(contour):
                                del paw.contourList[self.frame][index]
                                return
                        else:
                            # And check if they are the same as the contour we're trying to delete. This is rather crude, so it might bite me in the ass
                            if (
                            deleteContour[0][0][0] == contour[0][0][0] and deleteContour[0][0][1] == contour[0][0][1]
                            and deleteContour[-1][0][0] == contour[-1][0][0] and len(deleteContour) == len(contour)):
                                del paw.contourList[self.frame][index]
                                return

#                    # Only delete if they have the same length
#                    if len(contour) == len(deleteContour):
#                        # Loop through both contours at the same time
#                        for point1, point2 in zip(contour, deleteContour):
#                            # If both coordinates are equal
#                            if point1[0][0] == point2[0][0] and point1[0][1] == point2[0][1]:
#                                # Add the index of the contour to the delete list
#                                deleteList.add(index)
#                    # If the list isn't empty
#                    if deleteList:
#                        # If the index of the contour isn't in the contourList, add it back to the contourList
#                        paw.contourList[self.frame] = [contour for index, contour in enumerate(paw.contourList[self.frame]) if index not in deleteList]

#                    # If either contour has a length of 1
#                    if len(deleteContour) == 1 or len(contour) == 1:
#                        if deleteContour[0][0][0] == contour[0][0][0] and len(deleteContour) == len(contour):
#                            del paw.contourList[self.frame][index]
#                            return
#                    else:
#                        # And check if they are the same as the contour we're trying to delete. This is rather crude, so it might bite me in the ass
#                        if deleteContour[0][0][0] == contour[0][0][0] and deleteContour[-1][0][0] == contour[-1][0][0] and len(deleteContour) == len(contour):
#                            del paw.contourList[self.frame][index]
#                            return




        
