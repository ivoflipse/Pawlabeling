import os
from collections import defaultdict

import numpy as np
from PySide import QtGui, QtCore

from widgets import entireplatewidget, pawswidget
from settings import configuration
from functions import io, utility, gui, calculations
from functions.pubsub import pub
import logging

from models import processingmodel

class ProcessingWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ProcessingWidget, self).__init__(parent)

        # Initialize num_frames, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0
        self.dog_name = ""

        self.logger = logging.getLogger("logger")
        self.processing_model = processingmodel.ProcessingModel()

        # Initialize our variables that will cache results
        self.average_data = defaultdict(list)
        self.paw_data = defaultdict(list)
        self.paw_labels = defaultdict(dict)
        self.paws = defaultdict(list)

        # This contains all the file paths for each dog_name
        self.file_paths = defaultdict(dict)

        # Create a label to display the measurement name
        self.nameLabel = QtGui.QLabel(self)

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.colors = configuration.colors
        self.paw_dict = configuration.paw_dict

        self.current_paw_index = 0

        self.toolbar = gui.Toolbar(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()

        # Create a list widget
        self.measurement_tree = QtGui.QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")
        self.measurement_tree.itemActivated.connect(self.load_file)

        self.contact_tree = QtGui.QTreeWidget(self)
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

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.nameLabel)
        self.layout.addWidget(self.entire_plate_widget)
        self.layout.addWidget(self.paws_widget)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.addWidget(self.measurement_tree)
        self.vertical_layout.addWidget(self.contact_tree)
        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addLayout(self.vertical_layout)
        self.horizontal_layout.addLayout(self.layout)
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

    def add_measurements(self):
        """
        This function calls the processing model to search for measurements in the measurement_folder
        It will then fill the tree making root nodes for each dog and making child nodes for each measurement
        If the measurement has already been labeled it will also be marked as green instead of the default black.
        """
        # Find all the file_paths and load them into self.file_paths
        file_paths = self.processing_model.load_measurements()
        # Clear any existing measurements
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        for dog_name, file_paths in file_paths.items():
            root_item = QtGui.QTreeWidgetItem(self.measurement_tree, [dog_name])
            for file_path in file_paths:
                childItem = QtGui.QTreeWidgetItem(root_item, [file_path])
                # Check if the measurement has already been store_results_folder
                if io.find_stored_file(dog_name, file_path) is not None:
                    # Change the foreground to green
                    childItem.setForeground(0, green_brush)

    def load_first_file(self):
        """
        To bootstrap the application, the main window calls this function to select the first item in the tree
        if there are any nodes in it, else it'll log a warning. Selecting an item in the tree will cause
        load_file to be called
        """
        # Check if the tree isn't empty, because else we can't load anything
        if self.measurement_tree.topLevelItemCount() > 0:
            # Select the first item in the tree
            self.measurement_tree.setCurrentItem(self.measurement_tree.topLevelItem(0).child(0))
            # TODO figure out why this isn't automatically triggered
            self.load_file()
        else:
            pub.sendMessage("update_statusbar", status="No measurements found")
            self.logger.warning(
                "No measurements found, please check the location for the measurements and restart the program")

    def load_file(self):
        # Get the text from the currentItem
        current_item = self.measurement_tree.currentItem()
        # Check if you didn't accidentally double clicked the dog instead of a measurement:
        try:
            self.dog_name = str(current_item.parent().text(0))
        except AttributeError:
            print("Double click the measurements, not the dog names!")
            return

        # Notify the model to update the dog_name + measurement_name if necessary
        self.measurement_name = str(current_item.text(0))
        self.processing_model.switch_measurements(self.measurement_name)
        self.processing_model.switch_dogs(self.dog_name)

        self.processing_model.load_file()

        ## Manage some GUI elements
        self.nameLabel.setText("Measurement name: {}".format(self.measurement_name))
        self.contact_tree.clear()

        # Try loading the results or track them if no results are found
        self.processing_model.load_all_results()

        # Update the contact tree
        self.update_contact_tree()

        # Initialize the current paw index, which we'll need for keep track of the labeling
        self.current_paw_index = 0

        # Select the first item in the contacts tree
        item = self.contact_tree.topLevelItem(self.current_paw_index)
        self.contact_tree.setCurrentItem(item)
        self.update_current_paw()

    def update_contact_tree(self):
        self.paw_labels = self.processing_model.paw_labels
        self.paw_data = self.processing_model.paw_data
        self.paws = self.processing_model.paws

        # Clear any existing contacts
        self.contact_tree.clear()
        # Add the paws to the contact_tree
        for index, paw in enumerate(self.paw_data[self.measurement_name]):
            rootItem = QtGui.QTreeWidgetItem(self.contact_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, self.paw_dict[self.paw_labels[self.measurement_name][index]])
            x, y, z = paw.shape
            rootItem.setText(2, str(z))  # Sets the frame count
            surface = np.max(calculations.pixel_count_over_time(paw) * configuration.sensor_surface)
            rootItem.setText(3, str(int(surface)))
            force = np.max(calculations.force_over_time(paw))
            rootItem.setText(4, str(int(force)))

    def update_current_paw(self):
        if (self.current_paw_index <= len(self.paws[self.measurement_name]) and
                    len(self.paws[self.measurement_name]) > 0):
            for index, paw_label in self.paw_labels[self.measurement_name].items():
                # Get the current row from the tree
                item = self.contact_tree.topLevelItem(index)
                item.setText(1, self.paw_dict[paw_label])

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    item.setBackground(idx, self.colors[paw_label])


            self.processing_model.update_current_paw(self.current_paw_index)

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

    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        #return False if self.contact_tree.findItems("0", Qt.MatchExactly, 0) == [] else True
        return True if self.paw_labels[self.measurement_name] else False

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

    def track_contacts(self, event=None):
        self.processing_model.track_contacts()

    def store_status(self, event=None):
        self.processing_model.store_status()

    def create_toolbar_actions(self):
        self.track_contacts_action = gui.create_action(text="&Track Contacts",
                                                       shortcut=QtGui.QKeySequence("CTRL+F"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "images/edit_zoom.png")),
                                                       tip="Using the tracker to find contacts",
                                                       checkable=False,
                                                       connection=self.track_contacts
        )

        self.store_status_action = gui.create_action(text="&Store",
                                                     shortcut=QtGui.QKeySequence("CTRL+S"),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/save-icon.png")),
                                                     tip="Mark the tracking as correct",
                                                     checkable=False,
                                                     connection=self.store_status
        )

        self.left_front_action = gui.create_action(text="Select Left Front",
                                                   shortcut=configuration.left_front,
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__), "images/LF-icon.png")),
                                                   tip="Select the Left Front paw",
                                                   checkable=False,
                                                   connection=self.select_left_front
        )

        self.left_hind_action = gui.create_action(text="Select Left Hind",
                                                  shortcut=configuration.left_hind,
                                                  icon=QtGui.QIcon(
                                                      os.path.join(os.path.dirname(__file__), "images/LH-icon.png")),
                                                  tip="Select the Left Hind paw",
                                                  checkable=False,
                                                  connection=self.select_left_hind
        )

        self.right_front_action = gui.create_action(text="Select Right Front",
                                                    shortcut=configuration.right_front,
                                                    icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                  "images/RF-icon.png")),
                                                    tip="Select the Right Front paw",
                                                    checkable=False,
                                                    connection=self.select_right_front
        )

        self.right_hind_action = gui.create_action(text="Select Right Hind",
                                                   shortcut=configuration.right_hind,
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__), "images/RH-icon.png")),
                                                   tip="Select the Right Hind paw",
                                                   checkable=False,
                                                   connection=self.select_right_hind
        )

        self.previous_paw_action = gui.create_action(text="Select Previous Paw",
                                                     shortcut=[configuration.previous_paw,
                                                               QtGui.QKeySequence(QtCore.Qt.Key_Down)],
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/backward.png")),
                                                     tip="Select the previous paw",
                                                     checkable=False,
                                                     connection=self.previous_paw
        )

        self.next_paw_action = gui.create_action(text="Select Next Paw",
                                                 shortcut=[configuration.next_paw,
                                                           QtGui.QKeySequence(QtCore.Qt.Key_Up)],
                                                 icon=QtGui.QIcon(
                                                     os.path.join(os.path.dirname(__file__), "images/forward.png")),
                                                 tip="Select the next paw",
                                                 checkable=False,
                                                 connection=self.next_paw
        )

        self.remove_label_action = gui.create_action(text="Delete Label From Paw",
                                                     shortcut=configuration.remove_label,
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "images/cancel-icon.png")),
                                                     tip="Delete the label from the paw",
                                                     checkable=False,
                                                     connection=self.remove_label
        )

        self.invalid_paw_action = gui.create_action(text="Mark Paw as Invalid",
                                                    shortcut=configuration.invalid_paw,
                                                    icon=QtGui.QIcon(
                                                        os.path.join(os.path.dirname(__file__),
                                                                     "images/trash-icon.png")),
                                                    tip="Mark the paw as invalid",
                                                    checkable=False,
                                                    connection=self.invalid_paw
        )

        self.undo_label_action = gui.create_action(text="Undo Label From Paw",
                                                   shortcut=QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Z),
                                                   icon=QtGui.QIcon(
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


