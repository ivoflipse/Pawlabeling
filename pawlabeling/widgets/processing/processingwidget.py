import os
from collections import defaultdict
import logging
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui
from pawlabeling.settings import settings
from pawlabeling.widgets.processing import contactswidget, entireplatewidget
from pawlabeling.widgets import measurementtree
from pawlabeling.models import model


class ProcessingWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ProcessingWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")
        self.model = model.model

        # Create a label to display the measurement name
        self.subject_name_label = QtGui.QLabel(self)
        self.session_name_label = QtGui.QLabel(self)
        self.measurement_name_label = QtGui.QLabel(self)

        self.label_layout = QtGui.QHBoxLayout()
        self.label_layout.addWidget(self.subject_name_label)
        self.label_layout.addWidget(self.session_name_label)
        self.label_layout.addWidget(self.measurement_name_label)
        self.label_layout.addStretch(1)

        self.settings = settings.settings
        self.colors = self.settings.colors
        self.contact_dict = self.settings.contact_dict

        self.toolbar = gui.Toolbar(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()

        self.measurement_tree = measurementtree.measurement_tree

        self.entire_plate_widget = entireplatewidget.EntirePlateWidget(self)
        self.entire_plate_widget.setMinimumWidth(self.settings.entire_plate_widget_width())
        self.entire_plate_widget.setMaximumHeight(self.settings.entire_plate_widget_height())

        self.contacts_widget = contactswidget.ContactWidgets(self)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addLayout(self.label_layout)
        self.layout.addWidget(self.entire_plate_widget)
        self.layout.addWidget(self.contacts_widget)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.addWidget(self.measurement_tree)
        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addLayout(self.vertical_layout)
        self.horizontal_layout.addLayout(self.layout)
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

        self.subscribe()
        pub.subscribe(self.put_subject, "put_subject")
        pub.subscribe(self.put_session, "put_session")
        pub.subscribe(self.changed_settings, "changed_settings")

    def changed_settings(self):
        self.entire_plate_widget.setMinimumWidth(self.settings.entire_plate_widget_width())
        self.entire_plate_widget.setMaximumHeight(self.settings.entire_plate_widget_height())
        for contact in self.contacts_widget.contacts_list:
            contact.setMinimumHeight(self.settings.contacts_widget_height())

    def put_subject(self):
        subject_name = "{} {}".format(self.model.subject.first_name, self.model.subject.last_name)
        self.subject_name_label.setText("Subject: {}\t".format(subject_name))

    def put_session(self):
        self.session_name_label.setText("Session: {}\t".format(self.model.session.session_name))

    def undo_label(self):
        self.previous_contact()
        self.remove_label()

    def remove_label(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        # Remove the label
        current_contact = self.get_current_contact()
        current_contact.contact_label = -2
        # Update the screen
        self.update_current_contact()

    def invalid_contact(self):
        # Check if we have any contacts available, else don't bother
        if not self.contacts_available():
            return

        current_contact = self.get_current_contact()
        current_contact.invalid = not current_contact.invalid
        self.get_current_contact()
        # Update the screen
        self.update_current_contact()

    def get_current_contact(self):
        current_contact = self.model.contacts[self.model.measurement_name][self.model.current_contact_index]
        # Toggle the button if its invalid
        if current_contact.invalid:
            if not self.invalid_contact_action.isChecked():
                self.invalid_contact_action.toggle()
        else:
            if self.invalid_contact_action.isChecked():
                self.invalid_contact_action.toggle()
        return current_contact

    def select_left_front(self):
        current_contact = self.get_current_contact()
        current_contact.contact_label = 0
        self.next_contact()

    def select_left_hind(self):
        current_contact = self.get_current_contact()
        current_contact.contact_label = 1
        self.next_contact()

    def select_right_front(self):
        current_contact = self.get_current_contact()
        current_contact.contact_label = 2
        self.next_contact()

    def select_right_hind(self):
        current_contact = self.get_current_contact()
        current_contact.contact_label = 3
        self.next_contact()

    def contacts_available(self):
        """
        This function checks if there is a contact with index 0, if not, the tree must be empty
        """
        return True if self.model.contacts[self.model.measurement_name] else False

    def previous_contact(self):
        if not self.contacts_available():
            return

        # We can't go to a previous contact
        if self.model.current_contact_index == 0:
            return

        self.model.current_contact_index -= 1
        self.get_current_contact()

        measurement_item = self.get_current_measurement_item()
        contact_item = measurement_item.child(self.model.current_contact_index)
        self.measurement_tree.setCurrentItem(contact_item)
        self.update_current_contact()

    def next_contact(self):
        if not self.contacts_available():
            return

        # We can't go further so return
        if self.model.current_contact_index == len(self.model.contacts[self.model.measurement_name]) - 1:
            return


        self.model.current_contact_index += 1
        self.get_current_contact()

        measurement_item = self.get_current_measurement_item()
        contact_item = measurement_item.child(self.model.current_contact_index)
        self.measurement_tree.setCurrentItem(contact_item)
        self.update_current_contact()

    def track_contacts(self, event=None):
        # Make the model track new contacts
        self.model.repeat_track_contacts()
        # Make sure every widget gets updated
        self.update_current_contact()

    def store_status(self, event=None):
        self.model.store_contacts()

    def changed_settings(self):
        # Update all the keyboard shortcuts
        self.left_front_action.setShortcut(self.settings.left_front())
        self.left_hind_action.setShortcut(self.settings.left_hind())
        self.right_front_action.setShortcut(self.settings.right_front())
        self.right_hind_action.setShortcut(self.settings.right_hind())
        self.previous_contact_action.setShortcut(self.settings.previous_contact())
        self.next_contact_action.setShortcut(self.settings.next_contact())
        self.invalid_contact_action.setShortcut(self.settings.invalid_contact())
        self.remove_label_action.setShortcut(self.settings.remove_label())

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
                                                                      "../images/save.png")),
                                                     tip="Mark the tracking as correct",
                                                     checkable=False,
                                                     connection=self.store_status
        )

        self.left_front_action = gui.create_action(text="Select Left Front",
                                                   shortcut=self.settings.left_front(),
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/LF.png")),
                                                   tip="Select the Left Front contact",
                                                   checkable=False,
                                                   connection=self.select_left_front
        )

        self.left_hind_action = gui.create_action(text="Select Left Hind",
                                                  shortcut=self.settings.left_hind(),
                                                  icon=QtGui.QIcon(
                                                      os.path.join(os.path.dirname(__file__),
                                                                   "../images/LH.png")),
                                                  tip="Select the Left Hind contact",
                                                  checkable=False,
                                                  connection=self.select_left_hind
        )

        self.right_front_action = gui.create_action(text="Select Right Front",
                                                    shortcut=self.settings.right_front(),
                                                    icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                  "../images/RF.png")),
                                                    tip="Select the Right Front contact",
                                                    checkable=False,
                                                    connection=self.select_right_front
        )

        self.right_hind_action = gui.create_action(text="Select Right Hind",
                                                   shortcut=self.settings.right_hind(),
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/RH.png")),
                                                   tip="Select the Right Hind contact",
                                                   checkable=False,
                                                   connection=self.select_right_hind
        )

        self.previous_contact_action = gui.create_action(text="Select Previous contact",
                                                         shortcut=[self.settings.previous_contact(),
                                                                   QtGui.QKeySequence(QtCore.Qt.Key_Down)],
                                                         icon=QtGui.QIcon(
                                                             os.path.join(os.path.dirname(__file__),
                                                                          "../images/backward.png")),
                                                         tip="Select the previous contact",
                                                         checkable=False,
                                                         connection=self.previous_contact
        )

        self.next_contact_action = gui.create_action(text="Select Next contact",
                                                     shortcut=[self.settings.next_contact(),
                                                               QtGui.QKeySequence(QtCore.Qt.Key_Up)],
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/forward.png")),
                                                     tip="Select the next contact",
                                                     checkable=False,
                                                     connection=self.next_contact
        )

        self.remove_label_action = gui.create_action(text="Delete Label From contact",
                                                     shortcut=self.settings.remove_label(),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/cancel.png")),
                                                     tip="Delete the label from the contact",
                                                     checkable=False,
                                                     connection=self.remove_label
        )

        self.invalid_contact_action = gui.create_action(text="Mark contact as Invalid",
                                                        shortcut=self.settings.invalid_contact(),
                                                        icon=QtGui.QIcon(
                                                            os.path.join(os.path.dirname(__file__),
                                                                         "../images/trash.png")),
                                                        tip="Mark the contact as invalid",
                                                        checkable=True,
                                                        connection=self.invalid_contact
        )

        self.undo_label_action = gui.create_action(text="Undo Label From contact",
                                                   shortcut=QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Z),
                                                   icon=QtGui.QIcon(
                                                       os.path.join(os.path.dirname(__file__),
                                                                    "../images/undo.png")),
                                                   tip="Delete the label from the contact",
                                                   checkable=False,
                                                   connection=self.undo_label
        )

        # TODO Not all actions are editable yet in the settings
        self.actions = [self.store_status_action, self.track_contacts_action,
                        "separator",
                        self.left_front_action, self.left_hind_action,
                        self.right_front_action, self.right_hind_action,
                        "separator",
                        self.previous_contact_action, self.next_contact_action,
                        "separator",
                        self.remove_label_action, self.invalid_contact_action, self.undo_label_action]

        for action in self.actions:
            if action == "separator":
                self.toolbar.addSeparator()
            else:
                self.toolbar.addAction(action)


