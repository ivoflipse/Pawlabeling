import os
import pickle

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np

from widget import Widget
import realtimetracker
import utility

class MainWidget(QWidget):
    def __init__(self, path, pickled, desktopFlag, parent=None):
        super(MainWidget, self).__init__(parent)
        desktop = desktopFlag

        # Initialize numframes, in case measurements aren't loaded
        self.numFrames = 256

        if desktop:
            # Set the size to something nice and large
            self.resize(2550, 1000) # Make these sizes more platform independent
            widget_size = [600, 600]
            self.degree = 4
        else:
            self.resize(1400, 800) # Make these sizes more platform independent
            widget_size = [800, 500]
            self.degree = 4

        # Create a label to display the measurement name
        self.nameLabel = QLabel()

        self.path = path
        self.pickled = pickled

        # Create a list widget
        self.measurementTree = QTreeWidget(self)
        self.measurementTree.setMaximumWidth(250)
        self.measurementTree.setMinimumWidth(100)
        self.measurementTree.setColumnCount(1)
        self.measurementTree.setHeaderLabel("Measurements")
        self.measurementTree.itemActivated.connect(self.setFileName)
        # Load the measurements from a default path and set the filename to the first file from the folder
        self.addMeasurements(path=path)

        self.contactTree = QTreeWidget(self)
        self.contactTree.setMaximumWidth(250)
        self.contactTree.setColumnCount(3)
        self.contactTree.setHeaderLabels(["Contacts", "Length", "Surface"])

        # Pick the first item (if any exist)
        self.measurementTree.setCurrentItem(self.measurementTree.topLevelItem(0).child(0))
        self.setFileName(None)

        self.widget = Widget(self.filename, self.measurement,
                             self.paws, self.degree,
                             widget_size,
                             self)

        self.widget.setMinimumWidth(600)


        # Create a slider
        self.slider = QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.numFrames - 1)
        self.slider.valueChanged.connect(self.sliderMoved)
        # Set the slider to the first frame
        self.sliderMoved(0)

        self.mainLayout = QHBoxLayout(self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.nameLabel)
        self.layout.addWidget(self.widget)
        self.layout.addWidget(self.slider)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.addWidget(self.measurementTree)
        self.verticalLayout.addWidget(self.contactTree)
        self.mainLayout.addLayout(self.verticalLayout)
        self.mainLayout.addLayout(self.layout)
        self.setLayout(self.mainLayout)


    def fastBackward(self):
        self.slideToLeft(fast=True)

    def fastForward(self):
        self.slideToRight(fast=True)

    def slideToLeft(self, fast=False):
        framediff = 1
        if fast:
            framediff = 10
        new_frame = self.frame - framediff
        if new_frame < 0:
            new_frame = 0
        self.slider.setValue(new_frame)

    def slideToRight(self, fast=True):
        framediff = 1
        if fast:
            framediff = 10
        new_frame = self.frame + framediff
        if new_frame > (self.numFrames - 1):
            new_frame = self.numFrames - 1
        self.slider.setValue(new_frame)

    def setFileName(self, event=None):
        # Get the text from the currentItem
        self.currentItem = self.measurementTree.currentItem()
        parentItem = str(self.currentItem.parent().text(0))
        currentItem = str(self.currentItem.text(0))
        # Get the path from the filenames dictionary
        self.filename = self.filenames[parentItem][currentItem]
        try:
            # Load the file with the new filename
            self.loadFile()
        except Exception, e:
            print "Can't load the file with filename: {}".format(self.filename)
            print e
        # Only call update if widget has already been created
        if hasattr(self, 'widget'):
            self.updateWidget()

    def loadFile(self):
        # Update the label
        self.nameLabel.setText(self.filename)
        # Pass the new measurement through to the widget
        self.measurement = utility.load(self.filename, padding=True)
        #self.measurement = readzebris.loadFile(self.filename) # This enabled reading Zebris files
        # Get the number of Frames for the slider
        self.height, self.width, self.numFrames = self.measurement.shape
        pickle = False
        found = False
        if pickle:
            # If its pickled, get it from its pickle folder
            found = self.loadPickled()
            # Add the paws to the contactTree
            self.addContacts()

        if not pickle or not found:
            self.trackContacts()

    def trackContacts(self):
        print "Track!"
        paws = realtimetracker.trackContours_graph(self.measurement)
        # Convert them to class objects
        self.paws = []
        for index, paw in enumerate(paws):
            self.paws.append(realtimetracker.Contact(paw))

        # Sort the contacts based on their position along the first dimension    
        self.paws = sorted(self.paws, key=lambda paw: paw.totalcentroid[0])

        # Add the paws to the contactTree
        self.addContacts()
        if hasattr(self, 'widget'):
            self.updateWidget()

    def findPickledFile(self, dogName, filename):
        # For the current filename, check if there's a pickled file, if so load it
        # Get the name of the dog       
        path = os.path.join(self.pickled, dogName)
        # If the folder exists
        if os.path.exists(path):
            inputPath = None
            # Check if the current file's name is in that folder
            for root, dirs, files in os.walk(path):
                for f in files:
                    name, ext = f.split('.') # name.pkl 
                    if name == filename:
                        inputFile = f
                        inputPath = os.path.join(path, inputFile)
                        return inputPath

    def loadPickled(self):
        self.dogName = self.filename.split('\\')[-2]
        # Get the measurements name
        file_name = self.filename.split('\\')[-1]
        inputPath = self.findPickledFile(self.dogName, file_name)
        # If an inputFile has been found, unpickle it
        if inputPath:
            #print "Found it!"
            import pickle

            input = open(inputPath, 'rb')
            self.paws = pickle.load(input)
            # Sort the paws
            self.paws = sorted(self.paws, key=lambda paw: paw.totalcentroid[0])
            return True
        return False

    def updateWidget(self):
        self.widget.newMeasurement(self.measurement, self.paws)
        # Reset the frame counter
        self.slider.setValue(0)
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.numFrames - 1)

    def addContacts(self):
        # Print how many contacts we found
        print "Number of paws found:", len(self.paws)
        print "Number of frames: ", [len(paw.frames) for paw in self.paws]

        # Clear any existing contacts
        self.contactTree.clear()
        for index, paw in enumerate(self.paws):
            rootItem = QTreeWidgetItem(self.contactTree) # , ["Contact %s" % index, len(paw.frames)]
            rootItem.setText(0, "Contact %s" % index)
            rootItem.setText(1, str(len(paw.frames)))
            # Calculate a crude measure of the paw surface
            width = paw.totalmaxx - paw.totalminx
            height = paw.totalmaxy - paw.totalminy
            surface = int(width * height)
            rootItem.setText(2, str(surface))

    def deleteContact(self):
        index = self.contactTree.currentIndex().row()
        del self.paws[index]
        # Redraw everything, its probably easier to separate this because only the paws have to be redrawn
        self.widget.newMeasurement(self.measurement, self.paws)
        # Update the contactTree
        self.addContacts()

    def addMeasurements(self, path):
        self.filenames = {}
        # Clear any existing measurements
        self.measurementTree.clear()
        # Create a green brush for coloring pickled measurements
        greenBrush = QBrush(QColor(46, 139, 87))
        # Walk through the folder and gather up all the files
        for idx, (root, dirs, files) in enumerate(os.walk(path)):
            if not dirs: # changed from == []
                # Add the name of the dog
                self.dogName = root.split("\\")[-1]
                # Create a tree item
                rootItem = QTreeWidgetItem(self.measurementTree, [self.dogName])
                # Create a dictionary to store all the measurements for each dog
                self.filenames[self.dogName] = {}
                for index, fname in enumerate(files):
                    # Create a path from the path and the filename
                    name = os.path.join(root, fname)
                    # Set the filename to the first file from the folder
                    if index is 0:
                        self.filename = name
                        # Store the path with the file name
                    self.filenames[self.dogName][fname] = name
                    childItem = QTreeWidgetItem(rootItem, [fname])
                    # Check if the measurement has already been pickled
                    if self.findPickledFile(self.dogName, fname) is not None:
                        # Change the foreground to green
                        childItem.setForeground(0, greenBrush)


    def checkPickleStatus(self, name): # This one isn't really working as intended
        # Open the status file, find the dog + filename and check if it has been pickled
        self.statusFilePath = os.path.join(self.pickled, "status")

        # Try opening the status file
        if os.path.exists(self.statusFilePath):
            statusFile = open(self.statusFilePath, "rb")
            # Get the measurement name from filename
            file_name = name.split('\\')[-1]
            for line in statusFile.readlines():
                if line: # Ignore empty lines
                    # Split the line
                    dogName, filename, status = line.split('\t')
                    # Check if we found a match
                    if dogName == self.dogName and filename == file_name:
                        # If the status is True, return True
                        if status == 'True': # We're reading a string, so its not a Boolean!
                            return True
                        else:
                            return False
        else: # Doesn't exist
            return False


    def createContact(self, event):
        # Make sure everything else gets calculated as well
        # Like a bounding box and whatnot
        # Update the display, so we can see where it is
        self.widget.newMeasurement(self.measurement, self.paws)


    def sliderMoved(self, frame):
        # This prints the index and location of the paws to the command line for debugging purposes
        pawLoc = []
        for index, paw in enumerate(self.paws):
            if frame in paw.contourList:
                if len(paw.contourList[frame]) > 0:
                    d = {frame: paw.contourList[frame]}
                    center, _, _, _, _ = realtimetracker.updateBoundingBox(d)
                    pawLoc.append((index, (int(center[0]), int(center[1]))))
        print "Slider moved to:", frame, " ".join([str(c) for c in pawLoc])
        try:
            self.frame = frame
            self.widget.changeFrame(self.frame)
            self.nameLabel.setText("Measurement name: {}".format(self.filename))
        except IndexError:
            print "Error: No image at index", frame

    def goodResult(self):
        """
        Calls storeStatus with True, which stores the pickled result and adds the status to a status file
        """
        self.storeStatus(status=True)
        self.currentItem.setTextColor(0, QColor(Qt.green))

    def storeStatus(self, status):
        """
        Pass this function the status of the tracking: good or bad.
        This function then creates a file in the pickled folder if it doesn't exist
        And stores the filename \t status on a new line
        """
        # Get the file's name
        self.file_name = self.filename.split('\\')[-1]
        # Try and create a folder to add store the pickled result
        self.createPickledFolder()
        # Only pickle the measurement if the tracking was good
        if status is True:
        # Store the pickled result
            self.pickleResult()

    def pickleResult(self):
        """
        Pickles the paws to the pickle folder with the name of the measurement as file name
        """
        # Open a file at this path with the file_name as name
        output = open("%s//%s.pkl" % (self.new_path, self.file_name), 'wb')
        # Pickle dump the file to the hard drive
        pickle.dump(self.paws, output)
        # Close the output file
        output.close()
        print "Pickled %s at location %s" % (self.file_name, self.new_path)
        self.createLookupTable()

        # Change the color of the measurement in the tree to green
        treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
        self.currentItem.setForeground(0, treeBrush)

    def createPickledFolder(self):
        """
        This function take a path and creates a folder called" pickled [current date]"
        Returns the path of the folder just created
        """
        # The name of the dog is the second last element in filename
        self.dogName = self.filename.split('\\')[-2]
        path = os.path.join(self.pickled, self.dogName)
        # If the folder doesn't exist create it
        if not os.path.exists(path):
            os.mkdir(path)

        self.new_path = path
        # Create a new folder in the base folder if it doesn't already exist
        if not os.path.exists(self.new_path):
            os.mkdir(self.new_path)

