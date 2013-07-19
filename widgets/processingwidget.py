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

from widgets import entireplatewidget, pawswidget, resultswidget
from settings import configuration
from functions import io, tracking, utility, gui


class ProcessingWidget(QWidget):
    def __init__(self, parent=None):
        super(ProcessingWidget, self).__init__(parent)

        # Initialize num_frames, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0
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

        self.toolbar = gui.Toolbar(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()

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

        self.entire_plate_widget = entireplatewidget.EntirePlateWidget(self)
        self.entire_plate_widget.setMinimumWidth(configuration.entire_plate_widget_width)
        self.entire_plate_widget.setMaximumHeight(configuration.entire_plate_widget_height)

        self.paws_widget = pawswidget.PawsWidget(self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.nameLabel)
        self.layout.addWidget(self.entire_plate_widget)
        self.layout.addWidget(self.paws_widget)
        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.addWidget(self.measurement_tree)
        self.vertical_layout.addWidget(self.contact_tree)
        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.addLayout(self.vertical_layout)
        self.horizontal_layout.addLayout(self.layout)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

    ## IO Functions
    def add_measurements(self):
        import zipfile
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
                    # Check if the file isn't compressed, else zip it and delete the original after loading
                    base_name, extension = os.path.splitext(file_name)
                    # TODO I shouldn't delete if I can't confirm I have the zip file
                    if extension != ".zip":
                        file_path = os.path.join(root, file_name)
                        io.convert_file_to_zip(file_path)
                        # Add the .zip extension
                        file_name += ".zip"

                    name = os.path.join(root, file_name)
                    # Store the path with the file name
                    self.file_names[dog_name][file_name] = name
                    childItem = QTreeWidgetItem(root_item, [file_name])
                    # Check if the measurement has already been store_results_folder
                    if io.find_stored_file(dog_name, file_name) is not None:
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
        data = io.load(self.file_name,  brand=configuration.brand)
        # I have to add padding globally again, because it messes up everything downstream
        # Pad the data, so it will find things that touch the edges
        x, y, z = data.shape
        self.measurement = np.zeros((x+2, y+2, z), np.float32)
        self.measurement[1:-1, 1:-1, :] = data

        # Check the orientation of the plate and make sure its left to right
        self.measurement = io.fix_orientation(self.measurement)
        # Get the number of frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        # Get the normalizing factor for the color bars
        self.n_max = self.measurement.max()
        # And pass it to the paws_widget, so they all are scaled to the same color bar
        self.paws_widget.update_n_max(self.n_max)
        # Update the measurement data for the entire plate widget
        self.entire_plate_widget.new_measurement(self.measurement, self.measurement_name)

        ## Manage some GUI elements
        self.nameLabel.setText("Measurement name: {}".format(self.file_name))
        self.contact_tree.clear()

        # Try loading the results
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

    def load_all_results(self):
        """
        Check if there if any measurements for this dog have already been processed
        If so, retrieve the data and convert them to a usable format
        """
        # Iterate through all measurements for this dog
        self.currentItem = self.measurement_tree.currentItem()
        dog_name = str(self.currentItem.parent().text(0))
        file_names = self.file_names[dog_name]

        # Clear the average data
        self.average_data.clear()

        for file_name in file_names:
            measurement_name = file_name
            # Refresh the cache, it might be stale
            if measurement_name in self.paws:
                self.paws[measurement_name] = []
                self.paw_labels[measurement_name] = {}
                self.paw_data[measurement_name] = []

            stored_results = io.load_results(dog_name, measurement_name)
            # If we have results, stick them in their respective variable
            if stored_results:
                self.paw_labels[measurement_name] = stored_results["paw_labels"]
                for index, paw_data in stored_results["paw_data"].items():
                    self.paw_data[measurement_name].append(paw_data)

                    # TODO make sure this is never called when there isn't actually any data
                    # Check if n_max happens to be larger here
                    max_data = np.max(paw_data)
                    if max_data > self.n_max:
                        self.n_max = max_data
                        # And don't forget to send an update. Though this would only have to happen once
                        self.paws_widget.update_n_max(self.n_max)

                    paw = utility.Contact(stored_results["paw_results"][index], restoring=True)
                    self.paws[measurement_name].append(paw)

                # Until I've moved everything to be dictionary based, here's code to sort the paws + paw_data
                # Fancy pants code found here:
                # http://stackoverflow.com/questions/9764298/is-it-possible-to-sort-two-listswhich-reference-each-other-in-the-exact-same-w
                self.paws[measurement_name], self.paw_data[measurement_name] = zip(*sorted(
                    zip(self.paws[measurement_name], self.paw_data[measurement_name]),
                    key=lambda pair: pair[0].frames[0]))

                for index, data in enumerate(self.paw_data[measurement_name]):
                    paw_label = self.paw_labels[measurement_name][index]
                    if paw_label >= 0:
                        normalized_data = utility.normalize_paw_data(data)
                        self.average_data[paw_label].append(normalized_data)


    def store_status(self):
        """
        This function creates a file in the store_results_folder folder if it doesn't exist
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io.create_results_folder(self.dog_name)
        # Try storing the results
        try:
            io.results_to_json(self.new_path, self.dog_name, self.measurement_name,
                               self.paw_labels, self.paws, self.paw_data)
            print("The results have been stored")
            # Change the color of the measurement in the tree to green
            treeBrush = QBrush(QColor(46, 139, 87)) # RGB Sea Green
            self.currentItem.setForeground(0, treeBrush)
        except Exception as e:
            print("Storing failed!", e)

    ## Tracking
    def track_contacts(self):
        print("Track!")
        paws = tracking.track_contours_graph(self.measurement)

        # Make sure we don't have any paws stored if we're tracking again
        self.paws[self.measurement_name] = []
        self.paw_labels[self.measurement_name] = {}
        self.paw_data[self.measurement_name] = []

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

        # Initialize average_data if there's an empty paw
        for key in range(4):
            if not self.average_data:
                self.average_data[key] = np.zeros((15,15))

        self.initialize_widgets()

    ## GUI
    def initialize_widgets(self):
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
        self.remove_label()

    def remove_label(self):
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
        if self.current_paw_index <= len(self.paws[self.measurement_name]) and len(
                self.paws[self.measurement_name]) > 0:
            for index, paw_label in self.paw_labels[self.measurement_name].items():
                # Get the current row from the tree
                item = self.contact_tree.topLevelItem(index)
                item.setText(1, self.paw_dict[paw_label])

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    item.setBackground(idx, self.colors[paw_label])

            # Update the bounding boxes
            self.entire_plate_widget.update_bounding_boxes(self.paw_labels[self.measurement_name],
                                                           self.current_paw_index)
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


    def create_toolbar_actions(self):
        self.track_contacts_action = gui.create_action(text="&Track Contacts",
                                                       shortcut=QKeySequence("CTRL+F"),
                                                       icon=QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "images/edit_zoom.png")),
                                                       tip="Using the tracker to find contacts",
                                                       checkable=False,
                                                       connection=self.track_contacts
        )

        self.store_status_action = gui.create_action(text="&Store",
                                                     shortcut=QKeySequence("CTRL+S"),
                                                     icon=QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/save-icon.png")),
                                                     tip="Mark the tracking as correct",
                                                     checkable=False,
                                                     connection=self.store_status
        )

        self.left_front_action = gui.create_action(text="Select Left Front",
                                                   shortcut=configuration.left_front,
                                                   icon=QIcon(
                                                       os.path.join(os.path.dirname(__file__), "images/LF-icon.png")),
                                                   tip="Select the Left Front paw",
                                                   checkable=False,
                                                   connection=self.select_left_front
        )

        self.left_hind_action = gui.create_action(text="Select Left Hind",
                                                  shortcut=configuration.left_hind,
                                                  icon=QIcon(
                                                      os.path.join(os.path.dirname(__file__), "images/LH-icon.png")),
                                                  tip="Select the Left Hind paw",
                                                  checkable=False,
                                                  connection=self.select_left_hind
        )

        self.right_front_action = gui.create_action(text="Select Right Front",
                                                    shortcut=configuration.right_front,
                                                    icon=QIcon(os.path.join(os.path.dirname(__file__),
                                                                            "images/RF-icon.png")),
                                                    tip="Select the Right Front paw",
                                                    checkable=False,
                                                    connection=self.select_right_front
        )

        self.right_hind_action = gui.create_action(text="Select Right Hind",
                                                   shortcut=configuration.right_hind,
                                                   icon=QIcon(
                                                       os.path.join(os.path.dirname(__file__), "images/RH-icon.png")),
                                                   tip="Select the Right Hind paw",
                                                   checkable=False,
                                                   connection=self.select_right_hind
        )

        self.previous_paw_action = gui.create_action(text="Select Previous Paw",
                                                     shortcut=[configuration.previous_paw, QKeySequence(Qt.Key_Down)],
                                                     icon=QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/backward.png")),
                                                     tip="Select the previous paw",
                                                     checkable=False,
                                                     connection=self.previous_paw
        )

        self.next_paw_action = gui.create_action(text="Select Next Paw",
                                                 shortcut=[configuration.next_paw, QKeySequence(Qt.Key_Up)],
                                                 icon=QIcon(
                                                     os.path.join(os.path.dirname(__file__), "images/forward.png")),
                                                 tip="Select the next paw",
                                                 checkable=False,
                                                 connection=self.next_paw
        )

        self.remove_label_action = gui.create_action(text="Delete Label From Paw",
                                                     shortcut=configuration.remove_label,
                                                     icon=QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/cancel-icon.png")),
                                                     tip="Delete the label from the paw",
                                                     checkable=False,
                                                     connection=self.remove_label
        )

        self.invalid_paw_action = gui.create_action(text="Mark Paw as Invalid",
                                                    shortcut=configuration.invalid_paw,
                                                    icon=QIcon(
                                                        os.path.join(os.path.dirname(__file__),
                                                                     "images/trash-icon.png")),
                                                    tip="Mark the paw as invalid",
                                                    checkable=False,
                                                    connection=self.invalid_paw
        )

        self.undo_label_action = gui.create_action(text="Undo Label From Paw",
                                                   shortcut=QKeySequence(Qt.CTRL + Qt.Key_Z),
                                                   icon=QIcon(
                                                       os.path.join(os.path.dirname(__file__), "images/undo-icon.png")),
                                                   tip="Delete the label from the paw",
                                                   checkable=False,
                                                   connection=self.undo_label
        )

        self.actions = [self.store_status_action, self.track_contacts_action, self.left_front_action,
                        self.left_hind_action,
                        self.right_front_action, self.right_hind_action, self.previous_paw_action, self.next_paw_action,
                        self.remove_label_action, self.invalid_paw_action, self.undo_label_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)


