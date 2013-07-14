#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from collections import defaultdict

from PySide.QtGui import *
import numpy as np
import os

from functions import utility, gui
from settings import configuration
from widgets import resultswidget

class AnalysisWidget(QTabWidget):
    def __init__(self, parent):
        super(AnalysisWidget, self).__init__(parent)

        # Initialize num_frames, in case measurements aren't loaded
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

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.colors = configuration.colors
        self.paw_dict = configuration.paw_dict

        self.toolbar = gui.Toolbar(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()


        # Change it so the measurement tree is now loaded with all the contacts it found
        # for that dog, organized by paw_label

        # Create a list widget
        self.measurement_tree = QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")

        #self.measurement_tree.itemActivated.connect(self.load_file)

        self.contact_tree = QTreeWidget(self)
        self.contact_tree.setMaximumWidth(300)
        self.contact_tree.setMinimumWidth(300)
        self.contact_tree.setColumnCount(5)
        self.contact_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contact_tree.columnCount()):
            self.contact_tree.setColumnWidth(column, 60)
        self.contact_tree.itemActivated.connect(self.switch_contacts)

        self.results_widget = resultswidget.ResultsWidget(self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.results_widget)
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

    def switch_contacts(self):
        pass

    def select_left_front(self):
        pass

    def select_left_hind(self):
        pass

    def select_right_front(self):
        pass

    def select_right_hind(self):
        pass

    def invalid_paw(self):
        pass


    def create_toolbar_actions(self):
        self.left_front_action = gui.create_action(text="Select Left Front",
                                                   shortcut=configuration.left_front,
                                                   icon=QIcon(os.path.join(os.path.dirname(__file__), "images/LF-icon.png")),
                                                   tip="Select the Left Front paw",
                                                   checkable=False,
                                                   connection=self.select_left_front
        )

        self.left_hind_action = gui.create_action(text="Select Left Hind",
                                                  shortcut=configuration.left_hind,
                                                  icon=QIcon(os.path.join(os.path.dirname(__file__), "images/LH-icon.png")),
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
                                                   icon=QIcon(os.path.join(os.path.dirname(__file__), "images/RH-icon.png")),
                                                   tip="Select the Right Hind paw",
                                                   checkable=False,
                                                   connection=self.select_right_hind
        )

        self.invalid_paw_action = gui.create_action(text="Mark Paw as Invalid",
                                                    shortcut=configuration.invalid_paw,
                                                    icon=QIcon(
                                                        os.path.join(os.path.dirname(__file__), "images/trash-icon.png")),
                                                    tip="Mark the paw as invalid",
                                                    checkable=False,
                                                    connection=self.invalid_paw
        )

        self.actions = [self.left_front_action, self.left_hind_action,
                        self.right_front_action, self.right_hind_action,
                        self.invalid_paw_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)
