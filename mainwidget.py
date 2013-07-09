#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import numpy as np
from PySide.QtCore import *
from PySide.QtGui import *

from entireplatewidget import EntirePlateWidget
from pawswidget import PawsWidget
import utility
from settings import configuration


class MainWidget(QWidget):
    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)

        # Initialize numframes, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0

        self.degree = configuration.degree

        # Create a label to display the measurement name
        self.nameLabel = QLabel(self)

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.colors = configuration.colors
        self.paw_dict = configuration.paw_dict

        self.current_paw_index = 0

        # Create a list widget
        self.measurement_tree = QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")
        self.measurement_tree.itemActivated.connect(self.load_file)
        # Load the measurements
        self.add_measurements(path=self.path)

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
        # TODO move this call to mainwindow so its not ran until AFTER everything has been initialized
        self.measurement_tree.setCurrentItem(self.measurement_tree.topLevelItem(0).child(0))

        self.entire_plate_widget = EntirePlateWidget(self)
        self.entire_plate_widget.setMinimumWidth(600)

        self.paws_widget = PawsWidget(self, self.n_max)

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
        self.layout.addWidget(self.entire_plate_widget)
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
        self.entire_plate_widget.change_frame(self.frame)

    def load_file(self):
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

        self.entire_plate_widget.measurement = self.measurement

        # Get the number of Frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        self.n_max = self.measurement.max()
        self.paws_widget.update_n_max(self.n_max)
        # Send the measurement to the widget
        self.entire_plate_widget.new_measurement(self.measurement)
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
        print("Track!")
        paws = utility.track_contours_graph(self.measurement)
        # Convert them to class objects
        self.paws = []
        self.paw_data = []
        self.average_data = []
        self.paw_labels = {}
        for index, paw in enumerate(paws):
            paw = utility.Contact(paw)
            self.paws.append(paw)

        # Sort the contacts based on their position along the first dimension    
        self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])

        # TODO refactor out this code so its in a separate function, somewhere else preferably
        # Get the maximum dimensions of the paws
        self.mx = 0
        self.my = 0
        for index, paw in enumerate(self.paws):
            data_slice = utility.convert_contour_to_slice(self.measurement, paw.contour_list)
            x, y, z = data_slice.shape
            self.paw_data.append(data_slice)
            if x > self.mx:
                self.mx = x
            if y > self.my:
                self.my = y

            # I've made -2 the label for unlabeled paws, -1 == unlabeled + selected
            paw_label = -2
            # Test if the paw touches the edge of the plate
            if utility.touches_edges(self.measurement, paw, padding=True):
                paw_label = -3  # Mark it as invalid
            elif utility.incomplete_step(data_slice):
                paw_label = -3
            self.paw_labels[index] = paw_label

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
        self.entire_plate_widget.new_paws(self.paws)
        self.entire_plate_widget.draw_gait_line()
        self.current_paw_index = 0
        self.update_current_paw()

    def undo_label(self):
        self.previous_paw()
        self.delete_label()

    def delete_label(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        # Remove the label
        self.paw_labels[self.current_paw_index] = -1
        # Update the screen
        self.update_current_paw()

    def invalid_paw(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return
            # I've picked -3 as the label for invalid paws
        self.paw_labels[self.current_paw_index] = -3
        # Update the screen
        self.update_current_paw()

    def select_left_front(self):
        if self.paw_labels[self.current_paw_index] != -3:
            self.paw_labels[self.current_paw_index] = 0
        self.next_paw()

    def select_left_hind(self):
        if self.paw_labels[self.current_paw_index] != -3:
            self.paw_labels[self.current_paw_index] = 1
        self.next_paw()

    def select_right_front(self):
        if self.paw_labels[self.current_paw_index] != -3:
            self.paw_labels[self.current_paw_index] = 2
        self.next_paw()

    def select_right_hind(self):
        if self.paw_labels[self.current_paw_index] != -3:
            self.paw_labels[self.current_paw_index] = 3
        self.next_paw()

    def update_current_paw(self):
        if self.current_paw_index <= len(self.paws) and len(self.paws) > 0:
            for index, paw_label in list(self.paw_labels.items()):
                # Get the current row from the tree
                item = self.contact_tree.topLevelItem(index)
                item.setText(1, self.paw_dict[paw_label])

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    item.setBackground(idx, self.colors[paw_label])

            # Update the bounding boxes
            self.entire_plate_widget.update_bounding_boxes(self.paw_labels, self.current_paw_index)
            # Update the paws widget
            self.paws_widget.update_paws(self.paw_labels, self.current_paw_index, self.paw_data, self.average_data)


    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        #return False if self.contact_tree.findItems("0", Qt.MatchExactly, 0) == [] else True
        return True if self.paw_labels else False

    def check_label_status(self):
        results = []
        for paw_label in list(self.paw_labels.values()):
            if paw_label == -2:
                results.append(True)
            else:
                results.append(False)
        return any(results)

    def previous_paw(self):
        if not self.contacts_available():
            return

        # If we haven't labeled the current paw yet, mark it as unselected
        if self.paw_labels[self.current_paw_index] == -1:
            self.paw_labels[self.current_paw_index] = -2

        self.current_paw_index -= 1
        if self.current_paw_index < 0:
            self.current_paw_index = 0

        # If we encounter an invalid paw and its not the first paw, skip this one
        if self.paw_labels[self.current_paw_index] == -3 and self.check_label_status():
            self.previous_paw()

        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def next_paw(self):
        if not self.contacts_available():
            return

        # If we haven't labeled the current paw yet, mark it as unselected
        if self.paw_labels[self.current_paw_index] == -1:
            self.paw_labels[self.current_paw_index] = -2

        self.current_paw_index += 1
        if self.current_paw_index >= len(self.paws):
            self.current_paw_index = len(self.paws) - 1

        # If we encounter an invalid paw and its not the last paw, skip this one
        if self.paw_labels[self.current_paw_index] == -3 and self.check_label_status():
            self.next_paw()  # Woops, recursive loop right here!

        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def switch_contacts(self):
        item = self.contact_tree.selectedItems()[0]
        self.current_paw_index = int(item.text(0))
        self.update_current_paw()

    def add_contacts(self):
        # Print how many contacts we found
        print("Number of paws found: {}".format(len(self.paws)))
        print("Starting frames: {}".format([paw.frames[0] for paw in self.paws]))

        # Clear any existing contacts
        self.contact_tree.clear()
        for index, paw in enumerate(self.paw_data):
            x, y, z = paw.shape
            rootItem = QTreeWidgetItem(self.contact_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, self.paw_dict[self.paw_labels[index]])
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
        # Create a green brush for coloring stored results
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
                        name = os.path.join(root, file_name)
                        # Set the file_name to the first file from the folder
                        if index is 0:
                            self.file_name = name

                        # Store the path with the file name
                        self.file_names[self.dog_name][file_name] = name
                        childItem = QTreeWidgetItem(root_item, [file_name])
                        # Check if the measurement has already been store_results_folder
                        if self.find_stored_file(self.dog_name, file_name) is not None:
                            # Change the foreground to green
                            childItem.setForeground(0, green_brush)

    def store_status(self):
        """
        This function creates a file in the store_results_folder folder if it doesn't exist
        """
        # Try and create a folder to add store the store_results_folder result
        self.create_results_folder()
        # Store the store_results_folder result
        try:
            #self.pickle_result()
            self.results_to_json()  # Switched from pickling to JSON
            print("The results have been stored")
            # Change the color of the measurement in the tree to green
            treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
            self.currentItem.setForeground(0, treeBrush)
        except Exception as e:
            print("Pickling failed!", e)

    def create_results_folder(self):
        """
        This function takes a path and creates a folder called
        Returns the path of the folder just created
        """
        # The name of the dog is the second last element in file_name
        self.new_path = os.path.join(self.store_path, self.dog_name)
        # Create a new folder in the base folder if it doesn't already exist
        if not os.path.exists(self.new_path):
            os.mkdir(self.new_path)

    def results_to_json(self):
        """
        This creates a json file for the current measurement and stores the results
        """
        import json
        import zlib

        json_file_name = "{}//{} labels.json".format(self.new_path, self.measurement_name)
        with open(json_file_name, "w+") as json_file:
            # Update somewhere in between
            results = {"dog_name": self.dog_name,
                       "measurement_name": self.measurement_name,
                       "paw_labels": self.paw_labels,
                       "paw_results": [paw.contact_to_dict() for paw in self.paws],
                       "paw_data": {}
            }

            for index, data in enumerate(self.paw_data):
                values = []
                rows, columns, frames = np.nonzero(data)
                for row, column, frame in zip(rows, columns, frames):
                    values.append("{:10.4f}".format(data[row, column, frame]))
                results["paw_data"][index] = [data.shape, rows.tolist(), columns.tolist(), frames.tolist(), values]

            json_file.seek(0)  # Rewind the file, so we overwrite it
            json_file.write(json.dumps(results))
            json_file.truncate()  # In case the new file is smaller

    def reconstruct_data(self, shape, rows, columns, frames, values):
        data = np.zeros(shape)
        for row, column, frame, value in zip(rows, columns, frames, values):
            data[row, column, frame] = float(value)
        return data

    def pickle_result(self):
        """
        Pickles the paws to the pickle folder with the name of the measurement as file name
        """
        import pickle
        # Open a file at this path with the file_name as name
        output = open("%s//%s labels.pkl" % (self.new_path, self.measurement_name), 'wb')

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
        print("Pickled %s at location %s" % (self.file_name, self.new_path))

    def load_pickled(self):
        import pickle

        input_path = self.find_stored_file(self.dog_name, self.measurement_name)
        # If an inputFile has been found, unpickle it
        if input_path:
            input_file = open(input_path, 'rb')
            self.paws = pickle.load(input_file)
            # Sort the paws
            self.paws = sorted(self.paws, key=lambda paw: paw.frames[0])
            return True
        return False

    def find_stored_file(self, dog_name, file_name):
        # For the current file_name, check if there's a store_results_folder file, if so load it
        # Get the name of the dog
        path = os.path.join(self.store_path, dog_name)
        # If the folder exists
        if os.path.exists(path):
            # Check if the current file's name is in that folder
            for root, dirs, files in os.walk(path):
                for f in files:
                    name, ext = f.split('.') # name.pkl
                    if name == file_name:
                        input_file = f
                        input_path = os.path.join(path, input_file)
                        return input_path