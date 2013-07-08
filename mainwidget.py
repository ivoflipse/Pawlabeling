import os
import pickle

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from entirePlateWidget import EntirePlateWidget
from pawswidget import PawsWidget
import utility
import numpy as np


class MainWidget(QWidget):
    def __init__(self, path, store_path, desktop_flag, parent=None):
        super(MainWidget, self).__init__(parent)
        desktop = desktop_flag

        # Initialize numframes, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0

        if desktop:
            # Set the size to something nice and large
            self.resize(2550, 1400) # Make these sizes more platform independent
            entire_plate_widget_size = [800, 800]
            self.degree = 6
        else:
            self.resize(1400, 800) # Make these sizes more platform independent
            entire_plate_widget_size = [800, 500]
            self.degree = 4

        # Create a label to display the measurement name
        self.nameLabel = QLabel(self)

        self.path = path
        self.store_path = store_path

        # TODO Make these variable shared between all widgets, possibly putting it in config files?
        self.colors = [
            QColor(Qt.green),
            QColor(Qt.darkGreen),
            QColor(Qt.red),
            QColor(Qt.darkRed),
            QColor(Qt.gray),
            QColor(Qt.white),
            QColor(Qt.yellow),
        ]

        # FYI the id's are 1 lower compared to iApp
        self.paw_dict = {
            0: "LF",
            1: "LH",
            2: "RF",
            3: "RH",
            -3: "Invalid",
            -2: "-1", # I've changed this
            -1: "-1"
        }

        self.current_paw_index = 0

        # Create a list widget
        self.measurement_tree = QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")
        self.measurement_tree.itemActivated.connect(self.load_file)
        # Load the measurements from a default path and set the file_name to the first file from the folder
        self.add_measurements(path=path)

        self.contact_tree = QTreeWidget(self)
        self.contact_tree.setMaximumWidth(300)
        self.contact_tree.setMinimumWidth(300)
        self.contact_tree.setColumnCount(5)
        self.contact_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contact_tree.columnCount()):
            self.contact_tree.setColumnWidth(column, 60)

        self.contact_tree.itemActivated.connect(self.switch_contacts)

        # Pick the first item (if any exist)
        self.measurement_tree.setCurrentItem(self.measurement_tree.topLevelItem(0).child(0))

        self.entirePlateWidget = EntirePlateWidget(self.degree,
                                                   entire_plate_widget_size,
                                                   self)

        self.paws_widget = PawsWidget(self, self.degree * 2, self.n_max)

        self.entire_plate_widget.setMinimumWidth(600)

        # Create a slider
        self.slider = QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(-1)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.slider_moved)
        self.slider_text = QLabel(self)
        self.slider_text.setText("Frame: 0")

        self.slider_layout = QHBoxLayout()
        self.slider_layout.addWidget(self.slider)
        self.slider_layout.addWidget(self.slider_text)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.nameLabel)
        self.layout.addWidget(self.entirePlateWidget)
        self.layout.addLayout(self.slider_layout)
        self.layout.addWidget(self.paws_widget)
        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.addWidget(self.measurement_tree)
        self.vertical_layout.addWidget(self.contact_tree)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addLayout(self.vertical_layout)
        self.main_layout.addLayout(self.layout)
        self.setLayout(self.main_layout)

    def fast_backward(self):
        self.change_slider(-1, fast=True)

    def fast_forward(self):
        self.change_slider(1, fast=True)

    def slide_to_left(self, fast=False):
        self.change_slider(-1, fast)

    def slide_to_right(self, fast=False):
        self.change_slider(1, fast)

    def change_slider(self, frame_diff, fast=False):
        if fast:
            frame_diff *= 10

        new_frame = self.frame + frame_diff
        if new_frame > self.num_frames:
            new_frame = self.num_frames % new_frame

        self.slider.setValue(new_frame)

    def slider_moved(self, frame):
        self.slider_text.setText("Frame: {}".format(frame))
        self.frame = frame
        self.entirePlateWidget.change_frame(self.frame)

    def load_file(self, event=None):
        # Get the text from the currentItem
        self.currentItem = self.measurement_tree.currentItem()
        parentItem = str(self.currentItem.parent().text(0))
        currentItem = str(self.currentItem.text(0))
        # Get the path from the file_names dictionary
        self.file_name = self.file_names[parentItem][currentItem]
        self.measurement_name = self.file_name.split("\\")[-1]
        self.dog_name = self.file_name.split("\\")[-2]
        # Pass the new measurement through to the widget
        self.measurement = utility.load(self.file_name, padding=True)
        #self.measurement = readzebris.load_file(self.file_name) # This enabled reading Zebris files
        # Check the orientation of the plate and make sure its left to right
        self.measurement = utility.fix_orientation(self.measurement)

        self.entirePlateWidget.measurement = self.measurement

        # Get the number of Frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        self.n_max = self.measurement.max()
        self.paws_widget.update_n_max(self.n_max)
        # Send the measurement to the widget
        self.entirePlateWidget.new_measurement(self.measurement)
        # Remove outdated info from the contact tree
        self.contact_tree.clear()
        # Reset all the stored values
        # TODO Cache these values in some way, so it makes labeling in subsequent measurements easier
        self.paws = []
        self.paw_data = []
        self.average_data = []
        self.paw_labels = {}
        # Reset the frame counter
        self.slider.setValue(-1)
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.num_frames - 1)
        self.nameLabel.setText("Measurement name: {}".format(self.file_name))

    def track_contacts(self):
        print "Track!"
        paws = utility.track_contours_graph(self.measurement)
        # Convert them to class objects
        self.paws = []
        self.paw_data = []
        self.average_data = []
        self.paw_labels = {}
        for index, paw in enumerate(paws):
            paw = utility.Contact(paw)
            self.paws.append(paw)
            self.paw_labels[index] = -1

        # Sort the contacts based on their position along the first dimension    
        self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])

        # TODO refactor out this code so its in a separate function, somewhere else preferably
        # Get the maximum dimensions of the paws
        self.mx = 0
        self.my = 0
        for paw in self.paws:
            data_slice = utility.convert_contour_to_slice(self.measurement, paw.contour_list)
            x, y, z = data_slice.shape
            self.paw_data.append(data_slice)
            if x > self.mx:
                self.mx = x
            if y > self.my:
                self.my = y

        for paw in self.paw_data:
            x, y, z = paw.shape
            offset_x, offset_y = int((self.mx - x) / 2), int((self.my - y) / 2)
            average_slice = np.zeros((self.mx, self.my))
            average_slice[offset_x:offset_x + x, offset_y:offset_y + y] = paw.max(axis=2)
            self.average_data.append(average_slice)

        # Update the shape of the paws widget
        self.paws_widget.update_shape(self.mx, self.my)
        # Add the paws to the contact_tree
        self.add_contacts()
        # Update the widget's paws too
        self.entirePlateWidget.new_paws(self.paws)
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

    def invalid_paw(self, event=None):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return
            # I've picked -3 as the label for invalid paws
        self.paw_labels[self.current_paw_index] = -3
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
                item = self.contact_tree.topLevelItem(index)
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
        return False if self.contact_tree.findItems("0", Qt.MatchExactly, 0) == [] else True

    def remove_selected_color(self):
        # Remove the color from the Contact Tree if its yellow
        item = self.contact_tree.topLevelItem(self.current_paw_index)
        if item.backgroundColor(0) == self.colors[-1]:
            for idx in range(item.columnCount()):
                item.setBackgroundColor(idx, Qt.white)

    def previous_paw(self, event=None):
        if not self.contacts_available():
            return

        self.current_paw_index -= 1
        if self.current_paw_index < 0:
            self.current_paw_index = 0

        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def next_paw(self, event=None):
        if not self.contacts_available():
            return

        self.current_paw_index += 1
        if self.current_paw_index >= len(self.paws):
            self.current_paw_index = len(self.paws) - 1

        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def switch_contacts(self, event=None):
        item = self.contact_tree.selectedItems()[0]
        self.current_paw_index = int(item.text(0))
        self.update_current_paw()

    def add_contacts(self):
        # Print how many contacts we found
        print "Number of paws found:", len(self.paws)
        print "Starting frames: ", [paw.frames[0] for paw in self.paws]

        # Clear any existing contacts
        self.contact_tree.clear()
        for index, paw in enumerate(self.paw_data):
            x, y, z = paw.shape
            rootItem = QTreeWidgetItem(self.contact_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, "-1")
            rootItem.setText(2, str(z))  # Sets the frame count
            surface = np.max([np.count_nonzero(paw[:, :, frame]) for frame in range(z)])
            rootItem.setText(3, str(int(surface)))
            force = np.max(np.sum(np.sum(paw, axis=0), axis=0))
            rootItem.setText(4, str(int(force)))

        self.current_paw_index = 0

    def add_measurements(self, path):
        self.file_names = {}
        # Clear any existing measurements
        self.measurement_tree.clear()
        # Create a green brush for coloring store_path measurements
        green_brush = QBrush(QColor(46, 139, 87))
        # Walk through the folder and gather up all the files
        for idx, (root, dirs, files) in enumerate(os.walk(path)):
            if not dirs: # changed from == []
                # Add the name of the dog
                self.dog_name = root.split("\\")[-1]
                # Create a tree item
                root_item = QTreeWidgetItem(self.measurement_tree, [self.dog_name])
                # Create a dictionary to store all the measurements for each dog
                self.file_names[self.dog_name] = {}
                for index, file_name in enumerate(files):
                    # Ignoring the running trials for now
                    # TODO add a more elegant way to skip parts of the data
                    if file_name[0] != "d":
                        # Create a path from the path and the file_name
                        name = os.path.join(root, file_name)
                        # Set the file_name to the first file from the folder
                        if index is 0:
                            self.file_name = name

                        # Store the path with the file name
                        self.file_names[self.dog_name][file_name] = name
                        childItem = QTreeWidgetItem(root_item, [file_name])
                        # Check if the measurement has already been store_path
                        if self.find_pickled_file(self.dog_name, file_name) is not None:
                            # Change the foreground to green
                            childItem.setForeground(0, green_brush)

    def store_status(self):
        """
        This function creates a file in the store_path folder if it doesn't exist
        """
        # Try and create a folder to add store the store_path result
        self.create_results_folder()
        # Store the store_path result
        try:
            #self.pickle_result()
            self.dump_to_json()  # Switched from pickling to JSON

            # Change the color of the measurement in the tree to green
            treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
            self.currentItem.setForeground(0, treeBrush)
            self.currentItem.setTextColor(0, QColor(Qt.green))
        except Exception, e:
            print "Pickling failed!", e

    def create_results_folder(self):
        """
        This function take a path and creates a folder called" store_path [current date]"
        Returns the path of the folder just created
        """
        # The name of the dog is the second last element in file_name
        path = os.path.join(self.store_path, self.dog_name)
        # If the folder doesn't exist create it
        if not os.path.exists(path):
            os.mkdir(path)

        self.new_path = path
        # Create a new folder in the base folder if it doesn't already exist
        if not os.path.exists(self.new_path):
            os.mkdir(self.new_path)

    def dump_to_json(self):
        """
        This creates or takes a json file for the current dog and fills or updates it with the new
        paw information.
        """
        import json
        with open("{}//{}.labels.json".format(self.new_path, self.dog_name), "wb") as json_file:
            # Read the existing data
            data = json.load(json_file)

            # If data is empty, create an empty dictionary
            if not data:
                data = {}
                
            # Update somewhere in between
            new_results = {}
            new_results["dog_name"] = self.dog_name
            new_results["measurement_name"] = self.measurement_name
            new_results["paw_labels"] = self.paw_labels
            new_results["paws"] = self.paws

            # Add the results to the results to be written to json
            data[self.measurement_name] = new_results

            json_file.seek(0)  # Rewind the file, so overwrite it
            json_file.write(json.dumps(data))
            json_file.truncate()  # In case the new file is smaller

    def pickle_result(self):
        """
        Pickles the paws to the pickle folder with the name of the measurement as file name
        """
        # Open a file at this path with the file_name as name
        output = open("%s//%s.labels.pkl" % (self.new_path, self.measurement_name), 'wb')

        # The result in this case will be the index + 3D slice + sideid
        results = []
        for index, paw in enumerate(self.paws):
            total_centroid, total_min_x, total_max_x, total_min_y, total_max_y = utility.update_bounding_box(
                paw.contour_list)
            paw_label = self.paw_labels.get(index, -1)
            results.append([index, paw_label,
                            int(total_min_x), int(total_max_x),
                            int(total_min_y), int(total_max_y),
                            paw.frames[0], paw.frames[-1]])

        # Pickle dump the file to the hard drive
        pickle.dump(results, output)
        # Close the output file
        output.close()
        print "Pickled %s at location %s" % (self.file_name, self.new_path)

    def load_pickled(self):
        input_path = self.find_pickled_file(self.dog_name, self.measurement_name)
        # If an inputFile has been found, unpickle it
        if input_path:
            input_file = open(input_path, 'rb')
            self.paws = pickle.load(input_file)
            # Sort the paws
            self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])
            return True
        return False

    def find_pickled_file(self, dogName, file_name):
        # For the current file_name, check if there's a store_path file, if so load it
        # Get the name of the dog
        path = os.path.join(self.store_path, dogName)
        # If the folder exists
        if os.path.exists(path):
            input_path = None
            # Check if the current file's name is in that folder
            for root, dirs, files in os.walk(path):
                for f in files:
                    name, ext = f.split('.') # name.pkl
                    if name == file_name:
                        input_file = f
                        input_path = os.path.join(path, input_file)
                        return input_path