#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import json
from collections import defaultdict

import numpy as np
from PySide.QtCore import *
from PySide.QtGui import *

from widgets.entireplatewidget import EntirePlateWidget
from widgets.pawswidget import PawsWidget
from settings import configuration
from helper_functions import io_functions, tracking, utility


class MainWidget(QWidget):
    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)

        # Initialize numframes, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0
        self.mx = 15
        self.my = 15
        self.dog_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict(list)
        self.paw_data = defaultdict(list)
        self.paw_labels = defaultdict(dict)
        self.paws = defaultdict(list)

        # This contains all the file_names for each dog_name
        self.file_names = defaultdict(dict)
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

        self.contact_tree = QTreeWidget(self)
        self.contact_tree.setMaximumWidth(300)
        self.contact_tree.setMinimumWidth(300)
        self.contact_tree.setColumnCount(5)
        self.contact_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contact_tree.columnCount()):
            self.contact_tree.setColumnWidth(column, 60)
        self.contact_tree.itemActivated.connect(self.switch_contacts)

        self.entire_plate_widget = EntirePlateWidget(self)
        self.entire_plate_widget.setMinimumWidth(configuration.entire_plate_widget_width)
        self.entire_plate_widget.setMaximumHeight(configuration.entire_plate_widget_height)

        self.paws_widget = PawsWidget(self)

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

    ## IO Functions
    def add_measurements(self):
        # Clear any existing file names
        self.file_names.clear()
        # Clear any existing measurements
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QBrush(QColor(46, 139, 87))

        # Walk through the folder and gather up all the files
        for idx, (root, dirs, files) in enumerate(os.walk(self.path)):
            if not dirs:
                # Add the name of the dog
                dog_name = root.split("\\")[-1]
                # Create a tree item
                root_item = QTreeWidgetItem(self.measurement_tree, [dog_name])
                # Create a dictionary to store all the measurements for each dog
                self.file_names[dog_name] = {}
                for index, file_name in enumerate(files):
                    name = os.path.join(root, file_name)
                      # Store the path with the file name
                    self.file_names[dog_name][file_name] = name
                    childItem = QTreeWidgetItem(root_item, [file_name])
                    # Check if the measurement has already been store_results_folder
                    if io_functions.find_stored_file(dog_name, file_name) is not None:
                        # Change the foreground to green
                        childItem.setForeground(0, green_brush)

    def load_first_file(self):
        # Select the first item in the tree
        self.measurement_tree.setCurrentItem(self.measurement_tree.topLevelItem(0).child(0))
        self.load_file()

    # TODO split this function into more reusable parts
    def load_file(self):
        # Get the text from the currentItem
        self.currentItem = self.measurement_tree.currentItem()
        parentItem = str(self.currentItem.parent().text(0))
        currentItem = str(self.currentItem.text(0))

        # Get the path from the file_names dictionary
        self.file_name = self.file_names[parentItem][currentItem]
        split_name = self.file_name.split("\\")
        self.measurement_name = split_name[-1]
        # Check if we have a new dog, in that case, clear the cached values
        if split_name[-2] != self.dog_name:
            self.dog_name = split_name[-2]
            self.clear_cached_values()

        # Pass the new measurement through to the widget
        self.measurement = io_functions.load(self.file_name, padding=True, brand=configuration.brand)
        # Check the orientation of the plate and make sure its left to right
        self.measurement = io_functions.fix_orientation(self.measurement)
        # Get the number of frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        # Get the normalizing factor for the color bars
        self.n_max = self.measurement.max()
        # And pass it to the paws_widget, so they all are scaled to the same color bar
        self.paws_widget.update_n_max(self.n_max)
        # Update the measurement data for the entire plate widget
        self.entire_plate_widget.new_measurement(self.measurement, self.measurement_name)

        ## Manage some GUI elements
        # Reset the frame counter
        self.slider.setValue(-1)
        # Remove outdated info from the contact tree
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.num_frames - 1)
        self.nameLabel.setText("Measurement name: {}".format(self.file_name))
        self.contact_tree.clear()

        self.load_all_results()

        # Check if there's any data for this measurement
        if self.paw_data[self.measurement_name]: # This might not return a bool
            self.initialize_widgets()
        else:
            self.track_contacts()

    def clear_cached_values(self):
        self.average_data.clear()
        self.paws.clear()
        self.paw_data.clear()
        self.paw_labels.clear()

    # TODO currently you can't reload a measurement if you've accidentally messed it up
    def load_all_results(self):
        """
        Check if there if any measurements for this dog have already been processed
        If so, retrieve the data and convert them to a usable format
        """
        # Iterate through all measurements for this dog
        self.currentItem = self.measurement_tree.currentItem()
        dog_name = str(self.currentItem.parent().text(0))
        file_names = self.file_names[dog_name]

        for file_name in file_names:
            measurement_name = file_name
            # Only load files we haven't already loaded
            # TODO if a file has been changed since I've loaded it, the cache might get stale
            # perhaps I should remove the values if you start tracking again or update a measurement in some way
            if measurement_name not in self.paws:
                stored_results = io_functions.load_results(dog_name, measurement_name)
                # If we have results, stick them in their respective variable
                if stored_results:
                    self.paw_labels[measurement_name] = stored_results["paw_labels"]
                    for index, paw_data in stored_results["paw_data"].items():
                        self.paw_data[measurement_name].append(paw_data)
                        paw = utility.Contact(stored_results["paw_results"][index], restoring=True)
                        self.paws[measurement_name].append(paw)

                    for _, results in stored_results.items():
                        paw_labels = stored_results["paw_labels"].values()
                        paw_data = stored_results["paw_data"].values()
                        for paw_label, data in zip(paw_labels, paw_data):
                            if paw_label >= 0:
                                normalized_data = utility.normalize_paw_data(data)
                                self.average_data[paw_label].append(normalized_data)
                                # TODO there's a problem now, that if I make a mistake with the labeling,
                                # I don't know how to reverse it

    def store_status(self):
        """
        This function creates a file in the store_results_folder folder if it doesn't exist
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io_functions.create_results_folder(self.dog_name)
        # Try storing the results
        try:
            self.results_to_json()  # Switched from pickling to JSON
            print("The results have been stored")
            # Change the color of the measurement in the tree to green
            treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
            self.currentItem.setForeground(0, treeBrush)
        except Exception as e:
            print("Pickling failed!", e)


    # TODO this might not work, since the structure of the variables has been altered
    def results_to_json(self):
        """
        This creates a json file for the current measurement and stores the results
        """
        json_file_name = "{}//{}.json".format(self.new_path, self.measurement_name)
        with open(json_file_name, "w+") as json_file:
            # Update somewhere in between
            results = {"dog_name": self.dog_name,
                       "measurement_name": self.measurement_name,
                       "paw_labels": self.paw_labels[self.measurement_name],
                       "paw_results": [paw.contact_to_dict() for paw in self.paws[self.measurement_name]],
                       "paw_data": {}
            }

            for index, data in enumerate(self.paw_data[self.measurement_name]):
                values = []
                rows, columns, frames = np.nonzero(data)
                for row, column, frame in zip(rows, columns, frames):
                    values.append("{:10.4f}".format(data[row, column, frame]))
                results["paw_data"][index] = [data.shape, rows.tolist(), columns.tolist(), frames.tolist(), values]

            json_file.seek(0)  # Rewind the file, so we overwrite it
            json_file.write(json.dumps(results))
            json_file.truncate()  # In case the new file is smaller


    ## Tracking
    def track_contacts(self):
        print("Track!")
        paws = tracking.track_contours_graph(self.measurement)
        # Convert them to class objects
        for index, paw in enumerate(paws):
            paw = utility.Contact(paw)
            self.paws[self.measurement_name].append(paw)

        # Sort the contacts based on their position along the first dimension    
        self.paws[self.measurement_name] = sorted(self.paws[self.measurement_name], key=lambda paw: paw.frames[0])

        for index, paw in enumerate(self.paws[self.measurement_name]):
            data_slice = utility.convert_contour_to_slice(self.measurement, paw.contour_list)
            self.paw_data[self.measurement_name].append(data_slice)
            # I've made -2 the label for unlabeled paws, -1 == unlabeled + selected
            paw_label = -2
            # Test if the paw touches the edge of the plate
            if utility.touches_edges(self.measurement, paw, padding=True):
                paw_label = -3  # Mark it as invalid
            elif utility.incomplete_step(data_slice):
                paw_label = -3
            self.paw_labels[self.measurement_name][index] = paw_label

        self.initialize_widgets()

    ## GUI
    def initialize_widgets(self):
        # Update the shape of the paws widget
        self.paws_widget.update_shape(self.mx, self.my)
        # Add the paws to the contact_tree
        self.add_contacts()
        # Update the widget's paws too
        self.entire_plate_widget.new_paws(self.paws)
        self.entire_plate_widget.draw_gait_line()
        self.current_paw_index = 0
        # Select the first item in the contacts tree
        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def undo_label(self):
        self.previous_paw()
        self.delete_label()

    def delete_label(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        # Check if any other paw has the label -1, if so change it to -2
        for index, paw_label in self.paw_labels[self.measurement_name].items():
            if paw_label == -1:
                self.paw_labels[self.measurement_name][index] = -2

        # Remove the label
        self.paw_labels[self.measurement_name][self.current_paw_index] = -1
        # Update the screen
        self.update_current_paw()

    def invalid_paw(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return
            # I've picked -3 as the label for invalid paws
        self.paw_labels[self.measurement_name][self.current_paw_index] = -3
        # Update the screen
        self.update_current_paw()

    def select_left_front(self):
        if self.paw_labels[self.measurement_name][self.current_paw_index] != -3:
            self.paw_labels[self.measurement_name][self.current_paw_index] = 0
        self.next_paw()

    def select_left_hind(self):
        if self.paw_labels[self.measurement_name][self.current_paw_index] != -3:
            self.paw_labels[self.measurement_name][self.current_paw_index] = 1
        self.next_paw()

    def select_right_front(self):
        if self.paw_labels[self.measurement_name][self.current_paw_index] != -3:
            self.paw_labels[self.measurement_name][self.current_paw_index] = 2
        self.next_paw()

    def select_right_hind(self):
        if self.paw_labels[self.measurement_name][self.current_paw_index] != -3:
            self.paw_labels[self.measurement_name][self.current_paw_index] = 3
        self.next_paw()

    def update_current_paw(self):
        if self.current_paw_index <= len(self.paws[self.measurement_name]) and len(self.paws[self.measurement_name]) > 0:
            for index, paw_label in self.paw_labels[self.measurement_name].items():
                # Get the current row from the tree
                item = self.contact_tree.topLevelItem(index)
                item.setText(1, self.paw_dict[paw_label])

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    item.setBackground(idx, self.colors[paw_label])

            # Update the bounding boxes
            self.entire_plate_widget.update_bounding_boxes(self.paw_labels[self.measurement_name], self.current_paw_index)
            # Update the paws widget
            self.paws_widget.update_paws(self.paw_labels, self.paw_data, self.average_data,
                                         self.current_paw_index, self.measurement_name)

    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        #return False if self.contact_tree.findItems("0", Qt.MatchExactly, 0) == [] else True
        return True if self.paw_labels else False

    def check_label_status(self):
        results = []
        for paw_label in list(self.paw_labels[self.measurement_name].values()):
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
        if self.current_paw_index >= len(self.paws[self.measurement_name]):
            self.current_paw_index = len(self.paws[self.measurement_name]) - 1

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
        # TODO move this to some logging library
        print("Number of paws found: {}".format(len(self.paws[self.measurement_name])))
        print("Starting frames: {}".format(" ".join([str(paw.frames[0]) for paw in self.paws[self.measurement_name]])))

        # Clear any existing contacts
        self.contact_tree.clear()
        for index, paw in enumerate(self.paw_data[self.measurement_name]):
            x, y, z = paw.shape
            rootItem = QTreeWidgetItem(self.contact_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, self.paw_dict[self.paw_labels[self.measurement_name][index]])
            rootItem.setText(2, str(z))  # Sets the frame count
            surface = np.max([np.count_nonzero(paw[:, :, frame]) for frame in range(z)])
            rootItem.setText(3, str(int(surface)))
            force = np.max(np.sum(np.sum(paw, axis=0), axis=0))
            rootItem.setText(4, str(int(force)))

        self.current_paw_index = 0
