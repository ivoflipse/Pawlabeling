import os
import pickle

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from entirePlateWidget import EntirePlateWidget
from pawswidget import PawsWidget
import realtimetracker
import utility
import numpy as np

class MainWidget(QWidget):
    def __init__(self, path, pickled, desktopFlag, parent=None):
        super(MainWidget, self).__init__(parent)
        desktop = desktopFlag

        # Initialize numframes, in case measurements aren't loaded
        self.numFrames = 248
        self.frame = 0
        self.nmax = 0

        if desktop:
            # Set the size to something nice and large
            self.resize(2550, 1400) # Make these sizes more platform independent
            entirePlateWidget_size = [800, 800]
            self.degree = 6
        else:
            self.resize(1400, 800) # Make these sizes more platform independent
            entirePlateWidget_size = [800, 500]
            self.degree = 4

        # Create a label to display the measurement name
        self.nameLabel = QLabel(self)

        self.path = path
        self.pickled = pickled

        # TODO Make these variable shared between all widgets
        self.colors = [
            QColor(Qt.green),
            QColor(Qt.darkGreen),
            QColor(Qt.red),
            QColor(Qt.darkRed),
            QColor(Qt.grey),
            QColor(Qt.white),
            QColor(Qt.yellow),
            ]

        # FYI the id's are 1 lower compared to iApp
        self.paw_dict = {
            0 : "LF",
            1 : "LH",
            2 : "RF",
            3 : "RH",
            -3 : "Invalid",
            -2 : "-1",  # I've changed this
            -1 : "-1"
        }

        self.current_paw_index = 0

        # Create a list widget
        self.measurementTree = QTreeWidget(self)
        self.measurementTree.setMaximumWidth(300)
        self.measurementTree.setMinimumWidth(300)
        self.measurementTree.setColumnCount(1)
        self.measurementTree.setHeaderLabel("Measurements")
        self.measurementTree.itemActivated.connect(self.loadFile)
        # Load the measurements from a default path and set the filename to the first file from the folder
        self.addMeasurements(path=path)

        self.contactTree = QTreeWidget(self)
        self.contactTree.setMaximumWidth(300)
        self.contactTree.setMinimumWidth(300)
        self.contactTree.setColumnCount(5)
        self.contactTree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contactTree.columnCount()):
            self.contactTree.setColumnWidth(column, 60)

        self.contactTree.itemActivated.connect(self.switch_contacts)

        # Pick the first item (if any exist)
        self.measurementTree.setCurrentItem(self.measurementTree.topLevelItem(0).child(0))

        self.entirePlateWidget = EntirePlateWidget(self.degree,
                             entirePlateWidget_size,
                             self)

        self.paws_widget = PawsWidget(self, self.degree*2, self.nmax)

        self.entirePlateWidget.setMinimumWidth(600)

        # Create a slider
        self.slider = QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(-1)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.sliderMoved)
        self.sliderText = QLabel(self)
        self.sliderText.setText("Frame: 0")

        self.sliderLayout = QHBoxLayout()
        self.sliderLayout.addWidget(self.slider)
        self.sliderLayout.addWidget(self.sliderText)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.nameLabel)
        self.layout.addWidget(self.entirePlateWidget)
        self.layout.addLayout(self.sliderLayout)
        self.layout.addWidget(self.paws_widget)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.addWidget(self.measurementTree)
        self.verticalLayout.addWidget(self.contactTree)
        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.addLayout(self.verticalLayout)
        self.mainLayout.addLayout(self.layout)
        self.setLayout(self.mainLayout)

    def fastBackward(self):
        self.change_slider(-1, fast=True)

    def fastForward(self):
        self.change_slider(1, fast=True)

    def slideToLeft(self, fast=False):
        self.change_slider(-1, fast)

    def slideToRight(self, fast=False):
        self.change_slider(1, fast)

    def change_slider(self, frame_diff, fast=False):
        if fast:
            frame_diff *= 10

        new_frame = self.frame + frame_diff
        if new_frame > self.numFrames:
            new_frame = self.numFrames % new_frame

        self.slider.setValue(new_frame)

    def sliderMoved(self, frame):
        self.sliderText.setText("Frame: {}".format(frame))
        self.frame = frame
        self.entirePlateWidget.changeFrame(self.frame)

    def loadFile(self, event=None):
        # Get the text from the currentItem
        self.currentItem = self.measurementTree.currentItem()
        parentItem = str(self.currentItem.parent().text(0))
        currentItem = str(self.currentItem.text(0))
        # Get the path from the filenames dictionary
        self.filename = self.filenames[parentItem][currentItem]
        # Update the label
        self.nameLabel.setText(self.filename)
        # Pass the new measurement through to the widget
        self.measurement = utility.load(self.filename, padding=True)
        #self.measurement = readzebris.loadFile(self.filename) # This enabled reading Zebris files
        # Check the orientation of the plate and make sure its left to right
        self.measurement = utility.fix_orientation(self.measurement)

        self.entirePlateWidget.measurement = self.measurement

        # Get the number of Frames for the slider
        self.height, self.width, self.numFrames = self.measurement.shape
        self.nmax = self.measurement.max()
        self.paws_widget.update_nmax(self.nmax)
        # Send the measurement to the widget
        self.entirePlateWidget.newMeasurement(self.measurement)
        # Remove outdated info from the contact tree
        self.contactTree.clear()
        # Reset all the stored values
        # TODO Cache these values in some way, so it makes labeling in subsequent measurements easier
        self.paws = []
        self.paw_data = []
        self.average_data = []
        self.paw_labels = {}
        # Reset the frame counter
        self.slider.setValue(-1)
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.numFrames - 1)
        self.nameLabel.setText("Measurement name: {}".format(self.filename))

    def trackContacts(self):
        print "Track!"
        paws = realtimetracker.trackContours_graph(self.measurement)
        # Convert them to class objects
        self.paws = []
        self.paw_data = []
        self.average_data = []
        self.paw_labels = {}
        for index, paw in enumerate(paws):
            paw = realtimetracker.Contact(paw)
            self.paws.append(paw)
            self.paw_labels[index] = -1

        # Sort the contacts based on their position along the first dimension    
        self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])

        # TODO refactor out this code so its in a separate function, somewhere else preferably
        # Get the maximum dimensions of the paws
        self.mx = 0
        self.my = 0
        for paw in self.paws:
            data_slice = utility.convertContourToSlice(self.measurement, paw.contourList)
            x, y, z = data_slice.shape
            self.paw_data.append(data_slice)
            if x > self.mx:
                self.mx = x
            if y > self.my:
                self.my = y

        for paw in self.paw_data:
            x, y, z = paw.shape
            offset_x, offset_y = int((self.mx - x)/2), int((self.my - y)/2)
            average_slice = np.zeros((self.mx, self.my))
            average_slice[offset_x:offset_x+x, offset_y:offset_y+y] = paw.max(axis=2)
            self.average_data.append(average_slice)

        # Update the shape of the paws widget
        self.paws_widget.update_shape(self.mx, self.my)
        # Add the paws to the contactTree
        self.addContacts()
        # Update the widget's paws too
        self.entirePlateWidget.newPaws(self.paws)
        self.current_paw_index = 0
        self.update_current_paw()

    def undo_label(self, event=None):
        if not self.contacts_available():
            return

        # Change the current paw index
        self.current_paw_index -= 1
        if self.current_paw_index < 0:
            self.current_paw_index = 0

        # Remove the label
        self.paw_labels[self.current_paw_index] = -1
        # Update the screen
        self.update_current_paw()

    def delete_label(self, event=None):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return
        # Remove the label
        self.paw_labels[self.current_paw_index] = -1
        # Update the screen
        self.update_current_paw()

    def select_left_front(self, event=None):
        self.paw_labels[self.current_paw_index] = 0
        self.next_paw()

    def select_left_hind(self, event=None):
        self.paw_labels[self.current_paw_index] = 1
        self.next_paw()

    def select_right_front(self, event=None):
        self.paw_labels[self.current_paw_index] = 2
        self.next_paw()

    def select_right_hind(self, event=None):
        self.paw_labels[self.current_paw_index] = 3
        self.next_paw()

    def update_current_paw(self):
        if self.current_paw_index <= len(self.paws) and len(self.paws) > 0:
            for index, paw_label in self.paw_labels.items():
                # Get the current row from the tree
                item = self.contactTree.topLevelItem(index)
                item.setText(1, self.paw_dict[paw_label])

                # If its not the currently selected paw, change the label to gibberish
                if self.current_paw_index != index and paw_label == -1:
                    paw_label = -2
                if self.current_paw_index == index:
                    paw_label = -1

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    item.setBackgroundColor(idx, self.colors[paw_label])

            # Update the bounding boxes
            self.entirePlateWidget.update_bounding_boxes(self.paw_labels, self.current_paw_index)
            # Update the paws widget
            self.paws_widget.update_paws(self.paw_labels, self.current_paw_index, self.paw_data, self.average_data)


    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        return False if self.contactTree.findItems("0", Qt.MatchExactly, 0) == [] else True

    def remove_selected_color(self):
        # Remove the color from the Contact Tree if its yellow
        item = self.contactTree.topLevelItem(self.current_paw_index)
        if item.backgroundColor(0) == self.colors[-1]:
            for idx in range(item.columnCount()):
                item.setBackgroundColor(idx, Qt.white)

    def previous_paw(self, event=None):
        if not self.contacts_available():
            return

        self.current_paw_index -= 1
        if self.current_paw_index < 0:
            self.current_paw_index = 0

        item = self.contactTree.topLevelItem(self.current_paw_index)
        self.contactTree.setCurrentItem(item)
        self.update_current_paw()

    def next_paw(self, event=None):
        if not self.contacts_available():
            return

        self.current_paw_index += 1
        if self.current_paw_index > len(self.paws):
            self.current_paw_index = len(self.paws)

        item = self.contactTree.topLevelItem(self.current_paw_index)
        self.contactTree.setCurrentItem(item)
        self.update_current_paw()

    def switch_contacts(self, event=None):
        item = self.contactTree.selectedItems()[0]
        self.current_paw_index = int(item.text(0))
        self.update_current_paw()

    def addContacts(self):
        # Print how many contacts we found
        print "Number of paws found:", len(self.paws)
        print "Starting frames: ", [paw.frames[0] for paw in self.paws]

        # Clear any existing contacts
        self.contactTree.clear()
        for index, paw in enumerate(self.paw_data):
            x, y, z = paw.shape
            rootItem = QTreeWidgetItem(self.contactTree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, "-1")
            rootItem.setText(2, str(z))  # Sets the frame count
            surface = np.max([np.count_nonzero(paw[:,:,frame]) for frame in range(z)])
            rootItem.setText(3, str(int(surface)))
            force = np.max(np.sum(np.sum(paw, axis=0), axis=0))
            rootItem.setText(4, str(int(force)))

        self.current_paw_index = 0

    def deleteContact(self):
        index = self.contactTree.currentIndex().row()
        # TODO make sure it gets deleted EVERYWHERE
        del self.paws[index]
        # Redraw everything, its probably easier to separate this because only the paws have to be redrawn
        self.entirePlateWidget.newMeasurement(self.measurement, self.paws)
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

    def storeStatus(self):
        """
        This function creates a file in the pickled folder if it doesn't exist
        """
        # Get the file's name
        self.file_name = self.filename.split('\\')[-1]
        # Try and create a folder to add store the pickled result
        self.createPickledFolder()
        # Store the pickled result
        try:
            self.pickleResult()
            # Change the color of the measurement in the tree to green
            treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
            self.currentItem.setForeground(0, treeBrush)
            self.currentItem.setTextColor(0, QColor(Qt.green))
        except Exception, e:
            print "Pickling failed!", e


    def pickleResult(self):
        """
        Pickles the paws to the pickle folder with the name of the measurement as file name
        """
        # Open a file at this path with the file_name as name
        output = open("%s//%s.labels.pkl" % (self.new_path, self.file_name), 'wb')

        # The result in this case will be the index + 3D slice + sideid
        results = []
        for index, paw in enumerate(self.paws):
            totalcentroid, totalminx, totalmaxx, totalminy, totalmaxy = utility.updateBoundingBox(paw.contourList)
            paw_label = self.paw_labels.get(index, -1)
            results.append([index, paw_label,
                            int(totalminx), int(totalmaxx),
                            int(totalminy), int(totalmaxy),
                            paw.frames[0], paw.frames[-1]])

        # Pickle dump the file to the hard drive
        pickle.dump(results, output)
        # Close the output file
        output.close()
        print "Pickled %s at location %s" % (self.file_name, self.new_path)

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

    def loadPickled(self):
        self.dogName = self.filename.split('\\')[-2]
        # Get the measurements name
        file_name = self.filename.split('\\')[-1]
        inputPath = self.findPickledFile(self.dogName, file_name)
        # If an inputFile has been found, unpickle it
        if inputPath:
            input = open(inputPath, 'rb')
            self.paws = pickle.load(input)
            # Sort the paws
            self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])
            return True
        return False