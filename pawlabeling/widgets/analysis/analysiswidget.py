from collections import defaultdict
import os
import logging
from PySide import QtGui
from PySide.QtCore import Qt
import numpy as np
from pubsub import pub
from pawlabeling.functions import gui, io
from pawlabeling.settings import configuration
from pawlabeling.widgets.analysis import resultswidget


class AnalysisWidget(QtGui.QTabWidget):
    def __init__(self, parent):
        super(AnalysisWidget, self).__init__(parent)

        # Initialize num_frames, in case measurements aren't loaded
        self.frame = 0
        self.n_max = 0
        self.subject_name = ""
        self.outlier_toggle = False
        self.logger = logging.getLogger("logger")

        # Initialize our variables that will cache results
        self.average_data = defaultdict(list)
        self.contact_data = defaultdict(list)
        self.contact_labels = defaultdict(dict)
        self.contacts = defaultdict(list)

        # This contains all the file_names for each subject_name
        self.file_names = defaultdict(dict)

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.colors = configuration.colors
        self.contact_dict = configuration.contact_dict

        self.toolbar = gui.Toolbar(self)

        # Create a list widget
        self.measurement_tree = QtGui.QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setMaximumHeight(200)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")
        self.measurement_tree.itemActivated.connect(self.load_all_results)

        self.contact_tree = QtGui.QTreeWidget(self)
        self.contact_tree.setMaximumWidth(300)
        self.contact_tree.setMinimumWidth(300)
        self.contact_tree.setColumnCount(5)
        self.contact_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contact_tree.columnCount()):
            self.contact_tree.setColumnWidth(column, 55)

        self.results_widget = resultswidget.ResultsWidget(self)

        # Create a slider
        self.slider = QtGui.QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(-1)
        self.slider.setMaximum(0)
        self.slider.setValue(-1)
        self.slider.valueChanged.connect(self.change_frame)
        self.slider_text = QtGui.QLabel(self)
        self.slider_text.setText("Frame: -1")

        self.slider_layout = QtGui.QHBoxLayout()
        self.slider_layout.addWidget(self.slider)
        self.slider_layout.addWidget(self.slider_text)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.results_widget)
        self.layout.addLayout(self.slider_layout)
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

        self.create_toolbar_actions()

        self.subscribe()

        pub.subscribe(self.clear_cached_values, "clear_cached_values")

    def subscribe(self):
        pub.subscribe(self.add_measurements, "get_file_paths")
        pub.subscribe(self.update_contact_tree, "analysis_results")

    def unsubscribe(self):
        pub.ubsubscribe(self.add_measurements, "get_file_paths")
        pub.ubsubscribe(self.update_contact_tree, "analysis_results")


    def add_measurements(self, file_paths):
        # Clear any existing measurements
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        for subject_name, file_paths in file_paths.items():
            root_item = QtGui.QTreeWidgetItem(self.measurement_tree, [subject_name])
            for file_path in file_paths:
                # Check if there are any results stored
                if io.find_stored_file(subject_name, file_path) is not None:
                    root_item.setForeground(0, green_brush)
                    break

        self.measurement_tree.sortItems(0, Qt.AscendingOrder)

    # def load_first_file(self):
    #     # Check if the tree isn't empty, because else we can't load anything
    #     if self.measurement_tree.topLevelItemCount() > 0:
    #         # Select the first item in the tree
    #         self.measurement_tree.setCurrentItem(self.measurement_tree.topLevelItem(0))
    #         self.load_all_results()
    #     else:
    #         pub.sendMessage("update_statusbar", status="No results found")
    #         self.logger.warning(
    #             "No results found, please check the location for the results and restart the program")

    def load_all_results(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        # Get the text from the currentItem
        self.subject_name = self.measurement_tree.currentItem().text(0)

        # Notify the model to update the subject_name + measurement_name if necessary
        pub.sendMessage("switch_subjects", subject_name=self.subject_name)
        # Blank out the measurement_name
        #pub.sendMessage("switch_measurements", measurement_name="")

        pub.sendMessage("clear_cached_values")
        self.contact_tree.clear()
        # Send a message so the model starts loading results
        pub.sendMessage("load_results", widget="analysis")

    def update_contact_tree(self, contacts, average_data, results, max_results):
        self.contact_tree.clear()
        self.max_length = 0

        for measurement_name, contacts in contacts.items():
            for index, contact in enumerate(contacts):
                if contact.length > self.max_length:
                    self.max_length = contact.length
                contact_label = contact.contact_label

                if contact_label >= 0:
                    rootItem = QtGui.QTreeWidgetItem(self.contact_tree)
                    rootItem.setText(0, str(index))
                    rootItem.setText(1, self.contact_dict[contact_label])
                    rootItem.setText(2, str(contact.length))
                    surface = np.max(contact.surface_over_time)
                    rootItem.setText(3, str(int(surface)))
                    force = np.max(contact.force_over_time)
                    rootItem.setText(4, str(int(force)))

                    for idx in range(rootItem.columnCount()):
                        rootItem.setBackground(idx, self.colors[contact_label])

        # Sort the items per label
        self.contact_tree.sortItems(1, Qt.AscendingOrder)
        # Update the slider's max value
        self.slider.setMaximum(self.max_length)

    def clear_cached_values(self):
        self.n_max = 0
        self.average_data.clear()
        self.contacts.clear()

    def change_frame(self, frame):
        self.slider_text.setText("Frame: {}".format(frame))
        self.frame = frame
        pub.sendMessage("analysis.change_frame", frame=self.frame)

    def filter_outliers(self, event=None):
        self.outlier_toggle = not self.outlier_toggle
        pub.sendMessage("filter_outliers", toggle=self.outlier_toggle)

    def put_measurement(self):
        # Check if the tree aint empty!
        if not self.measurement_tree.topLevelItemCount():
            return
            # Notify the model to update the subject_name + measurement_name if necessary
        self.measurement_name = self.measurement_tree.currentItem().text(0)
        measurement = self.measurements[self.measurement_name]
        pub.sendMessage("put_measurement", measurement=measurement)

        # Now get everything that belongs to the measurement, the contacts and the measurement_data
        pub.sendMessage("get_measurement_data")
        pub.sendMessage("get_contacts")

        self.measurement_name_label.setText("Measurement name: {}".format(measurement["measurement_name"]))

        # # Send a message so the model starts loading results
        # pub.sendMessage("load_results", widget="processing")
        pub.sendMessage("load_contacts")

    def show_average_results(self, evt=None):
        pass

    def create_toolbar_actions(self):
        self.filter_outliers_action = gui.create_action(text="&Track Contacts",
                                                       shortcut=QtGui.QKeySequence("CTRL+F"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/edit_zoom.png")),
                                                       tip="Filter outliers",
                                                       checkable=True,
                                                       connection=self.filter_outliers
        )

        self.show_average_results_action = gui.create_action(text="&Show Average results",
                                                     shortcut=QtGui.QKeySequence("CTRL+A"),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/force_graph_icon.png")),
                                                     tip="Switch to average results",
                                                     checkable=True,
                                                     connection=self.show_average_results
        )

        self.actions = [self.filter_outliers_action, self.show_average_results_action]

        for action in self.actions:
            self.toolbar.addAction(action)