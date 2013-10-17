import os
from collections import defaultdict
import logging
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.models import model
from pawlabeling.settings import settings

class MeasurementTree(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MeasurementTree, self).__init__(parent)
        self.logger = logging.getLogger("logger")
        self.model = model.model
        self.settings = settings.settings
        self.colors = self.settings.colors
        self.contact_dict = self.settings.contact_dict

        # Create a list widget
        self.measurement_tree = QtGui.QTreeWidget(self)
        self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setColumnCount(5)
        self.measurement_tree.setHeaderLabels(["Name", "Label", "Length", "Surface", "Force"])
        self.measurement_tree.itemActivated.connect(self.item_activated)
        self.measurement_tree.setItemsExpandable(False)

        # Set the widths of the columns
        self.measurement_tree.setColumnWidth(0, 75)
        for column in xrange(1, self.measurement_tree.columnCount()):
            self.measurement_tree.setColumnWidth(column, 55)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.measurement_tree)
        self.setLayout(self.layout)

        pub.subscribe(self.update_measurements_tree, "update_measurement_status")

    def select_initial_measurement(self):
        self.current_measurement_index = 0
        measurement_item = self.measurement_tree.topLevelItem(self.current_measurement_index)
        self.measurement_tree.setCurrentItem(measurement_item, True)
        # We need to set a measurement name, before we can get contacts from it
        self.put_measurement()
        # For the current measurement, select the first of each contact labels (if available)
        self.select_initial_contacts()

    def select_initial_contacts(self):
        measurement_item = self.measurement_tree.currentItem()
        measurement_name = measurement_item.text(0)
        lookup = {0:0, 1:0, 2:0, 3:0}
        for index in range(measurement_item.childCount()):
            contact = self.model.contacts[measurement_name][index]
            if contact.contact_label in lookup and not lookup[contact.contact_label]:
                self.model.put_contact(contact_id=contact.contact_id)
                lookup[contact.contact_label] = 1

    # TODO I should split this function up, such that reloading the tree is independent of setting indices and such
    def update_measurements_tree(self):
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        for measurement in self.model.measurements.values():
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree, [measurement])
            measurement_item.setText(0, measurement.measurement_name)
            measurement_item.setFirstColumnSpanned(True)
            measurement_item.setExpanded(True)

            for contact in self.model.contacts[measurement.measurement_name]:
                contact_item = QtGui.QTreeWidgetItem(measurement_item)
                contact_item.setText(0, str(contact.contact_id))
                contact_item.setText(1, self.contact_dict[contact.contact_label])
                contact_item.setText(2, str(contact.length))  # Sets the frame count
                max_surface = np.max(contact.surface_over_time)
                contact_item.setText(3, str(int(max_surface)))
                max_force = np.max(contact.force_over_time)
                contact_item.setText(4, str(int(max_force)))
                contact_item.setText(3, str(int(max_surface)))
                max_force = np.max(contact.force_over_time)
                contact_item.setText(4, str(int(max_force)))

                if contact.invalid:
                    color = self.colors[-3]
                else:
                    color = self.colors[contact.contact_label]
                color.setAlphaF(0.5)

                for idx in xrange(contact_item.columnCount()):
                    contact_item.setBackground(idx, color)

            # If several contacts have been labeled, marked the measurement
            if measurement.processed:
                for idx in xrange(measurement_item.columnCount()):
                    measurement_item.setForeground(idx, green_brush)

        # Sort the tree by measurement name
        self.measurement_tree.sortByColumn(0, Qt.AscendingOrder)
        # Initialize the current contact index, which we'll need for keep track of the labeling
        self.model.current_contact_index = 0
        self.model.current_measurement_index = 0

        measurement_item = self.get_current_measurement_item()
        self.measurement_tree.setCurrentItem(measurement_item, True)

    def update_current_contact(self):
        measurement_item = self.get_current_measurement_item()
        contact_item = measurement_item.child(self.model.current_contact_index)
        self.measurement_tree.setCurrentItem(contact_item)

    def item_activated(self):
        # Check if the tree aint empty!
        if not self.measurement_tree.topLevelItemCount():
            return

        current_item = self.measurement_tree.currentItem()
        if current_item.parent():
            self.put_contact()
        else:
            self.put_measurement()

    # TODO Change this so it first checks what we clicked on and then calls the right function
    def put_measurement(self):
        # Check if the tree aint empty!
        if not self.measurement_tree.topLevelItemCount():
            return

        current_item = self.measurement_tree.currentItem()
        # Only put the measurement if we selected a measurement
        if current_item.parent():
            return

        self.model.current_measurement_index = self.measurement_tree.indexOfTopLevelItem(current_item)
        # Notify the model to update the subject_name + measurement_name if necessary
        measurement_name = current_item.text(0)
        self.model.put_measurement(measurement_name=measurement_name)

    def put_contact(self):
        # Check to make sure the measurement is selected first
        current_item = self.measurement_tree.currentItem()
        measurement_item = current_item.parent()
        self.measurement_tree.setCurrentItem(measurement_item)
        self.put_measurement()
        # Now put the contact
        contact_id = int(current_item.text(0))  # Convert the unicode to int

        for index, contact in enumerate(self.model.contacts[self.model.measurement_name]):
            if contact.contact_id == contact_id:
                self.model.current_contact_index = index

        self.model.put_contact(contact_id=contact_id)

    def get_current_measurement_item(self):
        return self.measurement_tree.topLevelItem(self.model.current_measurement_index)

instances = []

# This function makes sure only one instance of the measurement tree is created
# that way it can be shared between different widgets
def get_measurement_tree():
    if not instances:
        measurement_tree = MeasurementTree()
        instances.append(measurement_tree)
    return instances[0]