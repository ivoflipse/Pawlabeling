import os
from collections import defaultdict
import logging
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui
from pawlabeling.settings import configuration
from pawlabeling.widgets.processing import contactswidget
from pawlabeling.widgets.processing import entireplatewidget


class ProcessingWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ProcessingWidget, self).__init__(parent)

        # Initialize num_frames, in case measurements aren't loaded
        self.num_frames = 248
        self.frame = 0
        self.n_max = 0
        self.subject_name = ""

        self.logger = logging.getLogger("logger")

        # Create a label to display the measurement name
        self.subject_name_label = QtGui.QLabel(self)
        self.session_name_label = QtGui.QLabel(self)
        self.measurement_name_label = QtGui.QLabel(self)

        self.label_layout = QtGui.QHBoxLayout()
        self.label_layout.addWidget(self.subject_name_label)
        self.label_layout.addWidget(self.session_name_label)
        self.label_layout.addWidget(self.measurement_name_label)
        self.label_layout.addStretch(1)

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.colors = configuration.colors
        self.contact_dict = configuration.contact_dict

        self.current_contact_index = 0

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

        self.contacts_tree = QtGui.QTreeWidget(self)
        self.contacts_tree.setMaximumWidth(300)
        self.contacts_tree.setMinimumWidth(300)
        self.contacts_tree.setColumnCount(5)
        self.contacts_tree.setHeaderLabels(["Contacts", "Label", "Length", "Surface", "Force"])
        # Set the widths of the columns
        for column in range(self.contacts_tree.columnCount()):
            self.contacts_tree.setColumnWidth(column, 60)
        self.contacts_tree.itemActivated.connect(self.switch_contacts)

        self.entire_plate_widget = entireplatewidget.EntirePlateWidget(self)
        self.entire_plate_widget.setMinimumWidth(configuration.entire_plate_widget_width)
        self.entire_plate_widget.setMaximumHeight(configuration.entire_plate_widget_height)

        self.contacts_widget = contactswidget.contactsWidget(self)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addLayout(self.label_layout)
        self.layout.addWidget(self.entire_plate_widget)
        self.layout.addWidget(self.contacts_widget)
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

        #pub.subscribe(self.update_measurements_tree, "get_file_paths")
        pub.subscribe(self.put_subject, "put_subject")
        pub.subscribe(self.put_session, "put_session")
        pub.subscribe(self.update_measurements_tree, "update_measurements_tree")
        #pub.subscribe(self.update_contacts_tree, "update_contacts_tree")  # processing_results OLD MESSAGE
        pub.subscribe(self.stored_status, "stored_status")

    def put_subject(self, subject):
        self.subject = subject
        subject_name = "{} {}".format(self.subject["first_name"], self.subject["last_name"])
        self.subject_name_label.setText("Subject: {}\t".format(subject_name))

    def put_session(self, session):
        self.session = session
        self.session_name_label.setText("Session: {}\t".format(self.session["session_name"]))

    def update_measurements_tree(self, measurements):
        """
        This function is called when the model sends out the measurements as a response to get_measurements
        It will then fill the tree making a root node for the selected subject and a child node for the selected session
        then it will start making child nodes for each measurement within that session
        If the measurement has already been labeled it will also be marked as green instead of the default black.
        """
        # # Create a green brush for coloring stored results
        # green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))
        self.measurement_tree.clear()
        self.measurements = {}

        for measurement in measurements:
            self.measurements[measurement["measurement_name"]] = measurement
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree, [measurement])
            measurement_item.setText(0, measurement["measurement_name"])
            # How would I be able to check if this measurement has any contacts?
            #child_item.setForeground(0, green_brush)

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item)

    def load_file(self):
        # Notify the model to update the subject_name + measurement_name if necessary
        measurement_name = self.measurement_tree.currentItem().text(0)
        measurement = self.measurements[measurement_name]
        pub.sendMessage("put_measurement", measurement=measurement)

        # Now get everything that belongs to the measurement, the contacts and the measurement_data
        data = {'item_id': measurement["measurement_name"]}
        pub.sendMessage("get_measurement_data", data=data)
        pub.sendMessage("get_contacts", contact={})

        ## Manage some GUI elements
        self.measurement_name_label.setText("Measurement name: {}".format(measurement["measurement_name"]))
        self.contacts_tree.clear()

        # Send a message so the model starts loading results
        #pub.sendMessage("load_results", widget="processing")

    def update_contacts_tree(self, contacts):
        self.contacts = contacts

        # Clear any existing contacts
        self.contacts_tree.clear()
        # Add the contacts to the contacts_tree
        for index, contact in enumerate(self.contacts):
            rootItem = QtGui.QTreeWidgetItem(self.contacts_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, self.contact_dict[contact.contact_label])
            rootItem.setText(2, str(contact.length))  # Sets the frame count
            surface = np.max(contact.surface_over_time)
            rootItem.setText(3, str(int(surface)))
            force = np.max(contact.force_over_time)
            rootItem.setText(4, str(int(force)))

        # Initialize the current contact index, which we'll need for keep track of the labeling
        self.current_contact_index = 0

        # Select the first item in the contacts tree
        item = self.contacts_tree.topLevelItem(self.current_contact_index)
        self.contacts_tree.setCurrentItem(item)
        self.update_current_contact()

    def update_current_contact(self):
        if (self.current_contact_index <= len(self.contacts[self.measurement_name]) and
                    len(self.contacts[self.measurement_name]) > 0):
            for index, contact in enumerate(self.contacts[self.measurement_name]):
                contact_label = contact.contact_label
                # Get the current row from the tree
                item = self.contacts_tree.topLevelItem(index)
                item.setText(1, self.contact_dict[contact_label])

                # Update the colors in the contact tree
                for idx in range(item.columnCount()):
                    if contact_label >= 0:
                        item.setForeground(idx, self.colors[contact_label])

            pub.sendMessage("update_current_contact", current_contact_index=self.current_contact_index,
                            contacts=self.contacts)

    def undo_label(self):
        self.previous_contact()
        self.remove_label()

    def remove_label(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        # Check if any other contact has the label -1, if so change it to -2
        for index, contact in self.contacts[self.measurement_name]:
            if contact.contact_label == -1:
                contact.contact_label = -2

        # Remove the label
        current_contact = self.get_current_contact()
        current_contact.contact_label = -1
        # Update the screen
        self.update_current_contact()

    def invalid_contact(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        # I've picked -3 as the label for invalid contacts
        current_contact = self.get_current_contact()
        current_contact.contact_label = -3
        # Update the screen
        self.update_current_contact()

    def get_current_contact(self):
        current_contact = self.contacts[self.measurement_name][self.current_contact_index]
        return current_contact

    def select_left_front(self):
        current_contact = self.get_current_contact()
        if current_contact.contact_label != -3:
            current_contact.contact_label = 0
        self.next_contact()

    def select_left_hind(self):
        current_contact = self.get_current_contact()
        if current_contact.contact_label != -3:
            current_contact.contact_label = 1
        self.next_contact()

    def select_right_front(self):
        current_contact = self.get_current_contact()
        if current_contact.contact_label != -3:
            current_contact.contact_label = 2
        self.next_contact()

    def select_right_hind(self):
        current_contact = self.get_current_contact()
        if current_contact.contact_label != -3:
            current_contact.contact_label = 3
        self.next_contact()

    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        return True if self.contacts[self.measurement_name] else False

    def check_label_status(self):
        results = []
        for contact in self.contacts[self.measurement_name]:
            if contact.contact_label == -2:
                results.append(True)
            else:
                results.append(False)
        return any(results)

    def previous_contact(self):
        if not self.contacts_available():
            return

        # If we haven't labeled the current contact yet, mark it as unselected
        current_contact = self.get_current_contact()
        if current_contact.contact_label == -1:
            current_contact.contact_label = -2

        self.current_contact_index -= 1
        if self.current_contact_index < 0:
            self.current_contact_index = 0

        current_contact = self.get_current_contact()
        # If we encounter an invalid contact and its not the first contact, skip this one
        if current_contact.contact_label == -3 and self.check_label_status():
            self.previous_contact()

        item = self.contacts_tree.topLevelItem(self.current_contact_index)
        self.contacts_tree.setCurrentItem(item)
        self.update_current_contact()

    def next_contact(self):
        if not self.contacts_available():
            return

        # If we haven't labeled the current contact yet, mark it as unselected
        current_contact = self.get_current_contact()
        if current_contact.contact_label == -1:
            current_contact.contact_label = -2

        self.current_contact_index += 1
        if self.current_contact_index >= len(self.contacts[self.measurement_name]):
            self.current_contact_index = len(self.contacts[self.measurement_name]) - 1

        current_contact = self.get_current_contact()
        # If we encounter an invalid contact and its not the last contact, skip this one
        if current_contact.contact_label == -3 and self.check_label_status():
            self.next_contact()

        item = self.contacts_tree.topLevelItem(self.current_contact_index)
        self.contacts_tree.setCurrentItem(item)
        self.update_current_contact()

    def switch_contacts(self):
        item = self.contacts_tree.selectedItems()[0]
        self.current_contact_index = int(item.text(0))
        self.update_current_contact()

    def track_contacts(self, event=None):
        # Make the model track new contacts
        pub.sendMessage("track_contacts")
        # Make sure every widget gets updated
        self.update_current_contact()

    def store_status(self, event=None):
        pub.sendMessage("store_status")

    def stored_status(self, success):
        # If we were successful, change the color of the tree
        if success:
            current_item = self.measurement_tree.currentItem()
            green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))
            current_item.setForeground(0, green_brush)

    def create_toolbar_actions(self):
        self.track_contacts_action = gui.create_action(text="&Track Contacts",
                                                       shortcut=QtGui.QKeySequence("CTRL+F"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/edit_zoom.png")),
                                                       tip="Using the tracker to find contacts",
                                                       checkable=False,
                                                       connection=self.track_contacts
        )

        self.store_status_action = gui.create_action(text="&Store",
                                                     shortcut=QtGui.QKeySequence("CTRL+S"),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/save_icon.png")),
                                                     tip="Mark the tracking as correct",
                                                     checkable=False,
                                                     connection=self.store_status
        )

        self.left_front_action = gui.create_action(text="Select Left Front",
                                                   shortcut=configuration.left_front,
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/LF_icon.png")),
                                                   tip="Select the Left Front contact",
                                                   checkable=False,
                                                   connection=self.select_left_front
        )

        self.left_hind_action = gui.create_action(text="Select Left Hind",
                                                  shortcut=configuration.left_hind,
                                                  icon=QtGui.QIcon(
                                                      os.path.join(os.path.dirname(__file__), "../images/LH_icon.png")),
                                                  tip="Select the Left Hind contact",
                                                  checkable=False,
                                                  connection=self.select_left_hind
        )

        self.right_front_action = gui.create_action(text="Select Right Front",
                                                    shortcut=configuration.right_front,
                                                    icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                  "../images/RF_icon.png")),
                                                    tip="Select the Right Front contact",
                                                    checkable=False,
                                                    connection=self.select_right_front
        )

        self.right_hind_action = gui.create_action(text="Select Right Hind",
                                                   shortcut=configuration.right_hind,
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/RH_icon.png")),
                                                   tip="Select the Right Hind contact",
                                                   checkable=False,
                                                   connection=self.select_right_hind
        )

        self.previous_contact_action = gui.create_action(text="Select Previous contact",
                                                         shortcut=[configuration.previous_contact,
                                                                   QtGui.QKeySequence(QtCore.Qt.Key_Down)],
                                                         icon=QtGui.QIcon(
                                                             os.path.join(os.path.dirname(__file__),
                                                                          "../images/backward.png")),
                                                         tip="Select the previous contact",
                                                         checkable=False,
                                                         connection=self.previous_contact
        )

        self.next_contact_action = gui.create_action(text="Select Next contact",
                                                     shortcut=[configuration.next_contact,
                                                               QtGui.QKeySequence(QtCore.Qt.Key_Up)],
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/forward.png")),
                                                     tip="Select the next contact",
                                                     checkable=False,
                                                     connection=self.next_contact
        )

        self.remove_label_action = gui.create_action(text="Delete Label From contact",
                                                     shortcut=configuration.remove_label,
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/cancel_icon.png")),
                                                     tip="Delete the label from the contact",
                                                     checkable=False,
                                                     connection=self.remove_label
        )

        self.invalid_contact_action = gui.create_action(text="Mark contact as Invalid",
                                                        shortcut=configuration.invalid_contact,
                                                        icon=QtGui.QIcon(
                                                            os.path.join(os.path.dirname(__file__),
                                                                         "../images/trash_icon.png")),
                                                        tip="Mark the contact as invalid",
                                                        checkable=False,
                                                        connection=self.invalid_contact
        )

        self.undo_label_action = gui.create_action(text="Undo Label From contact",
                                                   shortcut=QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Z),
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/undo_icon.png")),
                                                   tip="Delete the label from the contact",
                                                   checkable=False,
                                                   connection=self.undo_label
        )

        self.actions = [self.store_status_action, self.track_contacts_action, self.left_front_action,
                        self.left_hind_action,
                        self.right_front_action, self.right_hind_action, self.previous_contact_action,
                        self.next_contact_action,
                        self.remove_label_action, self.invalid_contact_action, self.undo_label_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)


