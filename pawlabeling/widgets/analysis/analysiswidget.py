from collections import defaultdict
import os
import logging
from PySide import QtGui
from PySide.QtCore import Qt
import numpy as np
from pubsub import pub
from pawlabeling.functions import gui, io
from pawlabeling.settings import settings
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
        self.contacts = defaultdict(list)
        self.settings = settings.settings
        self.colors = self.settings.colors()
        self.contact_dict = self.settings.contact_dict()

        self.toolbar = gui.Toolbar(self)

        # Create a list widget
        self.measurement_tree = QtGui.QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setMaximumHeight(200)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabel("Measurements")
        self.measurement_tree.itemActivated.connect(self.put_measurement)

        self.contacts_tree = QtGui.QTreeWidget(self)
        self.contacts_tree.setMaximumWidth(300)
        self.contacts_tree.setMinimumWidth(300)
        self.contacts_tree.setColumnCount(5)
        self.contacts_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contacts_tree.columnCount()):
            self.contacts_tree.setColumnWidth(column, 55)

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
        self.vertical_layout.addWidget(self.contacts_tree)
        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addLayout(self.vertical_layout)
        self.horizontal_layout.addLayout(self.layout)
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

        self.subscribe()

        self.create_toolbar_actions()

        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.update_measurement, "put_measurement")

    def subscribe(self):
        pub.subscribe(self.update_measurements_tree, "update_measurements_tree")
        pub.subscribe(self.update_contacts_tree, "update_contacts_tree")

    def unsubscribe(self):
        pub.unsubscribe(self.update_measurements_tree, "update_measurements_tree")
        pub.unsubscribe(self.update_contacts_tree, "update_contacts_tree")

    def calculate_results(self):
        pub.sendMessage("calculate_results")

    def update_measurement(self, measurement):
        self.measurement_name = measurement.measurement_name

    def update_measurements_tree(self, measurements):
        self.measurement_tree.clear()

        for measurement in measurements.values():
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree, [measurement])
            measurement_item.setText(0, measurement.measurement_name)

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item, True)

    def update_contacts_tree(self, contacts):
        self.contacts = contacts
        self.max_length = 0
        # Clear any existing contacts
        self.contacts_tree.clear()
        # Add the contacts to the contacts_tree
        for contact in self.contacts[self.measurement_name]:
            if contact.length > self.max_length:
                self.max_length = contact.length
            rootItem = QtGui.QTreeWidgetItem(self.contacts_tree)
            rootItem.setText(0, str(contact.contact_id))
            rootItem.setText(1, self.contact_dict[contact.contact_label])
            rootItem.setText(2, str(contact.length))  # Sets the frame count
            surface = np.max(contact.surface_over_time)
            rootItem.setText(3, str(int(surface)))
            force = np.max(contact.force_over_time)
            rootItem.setText(4, str(int(force)))

            for idx in range(rootItem.columnCount()):
                rootItem.setBackground(idx, self.colors[contact.contact_label])

        # Initialize the current contact index, which we'll need for keep track of the labeling
        self.current_contact_index = 0

        # Select the first item in the contacts tree
        item = self.contacts_tree.topLevelItem(self.current_contact_index)
        self.contacts_tree.setCurrentItem(item)
        #self.update_current_contact()

        # Sort the items per label
        self.contacts_tree.sortItems(1, Qt.AscendingOrder)
        # Update the slider's max value
        self.slider.setMaximum(self.max_length)

    def clear_cached_values(self):
        self.n_max = 0
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
        measurement = {"measurement_name":self.measurement_name}
        pub.sendMessage("put_measurement", measurement=measurement)

        # Now get everything that belongs to the measurement, the contacts and the measurement_data
        pub.sendMessage("get_measurement_data")
        pub.sendMessage("get_contacts")

    # TODO Add a way to switch between looking at individual contacts to an average result
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