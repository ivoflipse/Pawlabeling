import os
from collections import defaultdict
import logging
import datetime
import numpy as np
import tables
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui
from pawlabeling.settings import configuration


class DatabaseWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder

        self.toolbar = gui.Toolbar(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()

        self.subject_tree = QtGui.QTreeWidget(self)
        self.subject_tree.setMinimumWidth(300)
        self.subject_tree.setMaximumWidth(400)
        self.subject_tree.setColumnCount(4)
        self.subject_tree.setHeaderLabels(["ID", "First Name", "Last Name", "Birthday"])

        self.subject_tree_layout = QtGui.QVBoxLayout()
        self.subject_tree_layout.addWidget(self.subject_tree)

        self.subject_id_label = QtGui.QLabel("Subject ID")
        self.birthday_label = QtGui.QLabel("Birthday")
        self.mass_label = QtGui.QLabel("Mass")
        self.first_name_label = QtGui.QLabel("First Name")
        self.last_name_label = QtGui.QLabel("Last Name")
        self.address_label = QtGui.QLabel("Address")
        self.city_label = QtGui.QLabel("City")
        self.phone_label = QtGui.QLabel("Phone")
        self.email_label = QtGui.QLabel("Email")

        self.subject_id = QtGui.QLineEdit()
        self.birthday = QtGui.QDateTimeEdit(QtCore.QDate.currentDate())
        self.birthday.setMinimumDate(QtCore.QDate.currentDate().addYears(-100))
        self.birthday.setMaximumDate(QtCore.QDate.currentDate())
        self.date_format = QtCore.QLocale.system().dateFormat(QtCore.QLocale.ShortFormat)
        self.birthday.setDisplayFormat(self.date_format)
        self.mass = QtGui.QLineEdit()
        self.first_name = QtGui.QLineEdit()
        self.last_name = QtGui.QLineEdit()
        self.address = QtGui.QLineEdit()
        self.city = QtGui.QLineEdit()
        self.phone = QtGui.QLineEdit()
        self.email = QtGui.QLineEdit()


        self.subject_fields = ["subject_id", "birthday", "mass", "first_name", "last_name",
                               "address", "city", "phone", "email"]

        self.subject_layout = QtGui.QGridLayout()
        self.subject_layout.setSpacing(10)
        self.subject_layout.addWidget(self.subject_id_label, 1, 0)
        self.subject_layout.addWidget(self.subject_id, 1, 1)
        self.subject_layout.addWidget(self.mass_label, 2, 0)
        self.subject_layout.addWidget(self.mass, 2, 1)
        self.subject_layout.addWidget(self.birthday_label, 2, 2)
        self.subject_layout.addWidget(self.birthday, 2, 3)
        self.subject_layout.addWidget(self.first_name_label, 3, 0)
        self.subject_layout.addWidget(self.first_name, 3, 1)
        self.subject_layout.addWidget(self.last_name_label, 3, 2)
        self.subject_layout.addWidget(self.last_name, 3, 3)
        self.subject_layout.addWidget(self.address_label, 4, 0)
        self.subject_layout.addWidget(self.address, 4, 1)
        self.subject_layout.addWidget(self.city_label, 4, 2)
        self.subject_layout.addWidget(self.city, 4, 3)
        self.subject_layout.addWidget(self.phone_label, 5, 0)
        self.subject_layout.addWidget(self.phone, 5, 1)
        self.subject_layout.addWidget(self.email_label, 5, 2)
        self.subject_layout.addWidget(self.email, 5, 3)

        self.session_name_label = QtGui.QLabel("Session Name")
        self.session_date_label = QtGui.QLabel("Session Date")
        self.session_time_label = QtGui.QLabel("Session Time")

        self.session_name = QtGui.QLineEdit()
        self.session_date = QtGui.QDateEdit(QtCore.QDate.currentDate())
        self.session_date.setMinimumDate(QtCore.QDate.currentDate().addYears(-100))
        self.session_date.setMaximumDate(QtCore.QDate.currentDate())
        self.session_date.setDisplayFormat(self.date_format)
        self.session_time = QtGui.QTimeEdit(QtCore.QTime.currentTime())
        #self.time_format = QtCore.QLocale.system().timeFormat(QtCore.QLocale.ShortFormat)
        self.session_time.setDisplayFormat(u"HH:mm")

        self.session_tree = QtGui.QTreeWidget(self)
        self.session_tree.setMinimumWidth(300)
        self.session_tree.setMaximumWidth(400)
        self.session_tree.setColumnCount(3)
        self.session_tree.setHeaderLabels(["Name", "Date", "Time"])

        self.session_layout = QtGui.QGridLayout()
        self.session_layout.setSpacing(10)
        self.session_layout.addWidget(self.session_name_label, 1, 0)
        self.session_layout.addWidget(self.session_name, 1, 1)
        self.session_layout.addWidget(self.session_date_label, 2, 0)
        self.session_layout.addWidget(self.session_date, 2, 1)
        self.session_layout.addWidget(self.session_time_label, 3, 0)
        self.session_layout.addWidget(self.session_time, 3, 1)

        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.addLayout(self.subject_layout)
        self.vertical_layout.addLayout(self.session_layout)
        self.vertical_layout.addWidget(self.session_tree)

        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addLayout(self.subject_tree_layout)
        self.horizontal_layout.addLayout(self.vertical_layout)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

        pub.subscribe(self.update_subject_id, "update_subject_id")

        # TODO check when to call this
        # Ask for a new id
        pub.sendMessage("get_new_subject_id")

    def create_subject(self):
        # TODO Check here if the required fields have been entered
        # Also add some validation, to check if they're acceptable

        subject = {}
        for field in self.subject_fields:
            if field == "birthday":
                date = getattr(self, field).date()
                subject[field] = date.toString(Qt.ISODate)
            elif field == "mass":
                mass = getattr(self, field).text()
                if not mass:
                    mass = 0
                subject[field] = float(mass)
            else:
                subject[field] = getattr(self, field).text()

        pub.sendMessage("create_subject", subject=subject)

    def create_session(self):
        session = {}
        session["session_name"] = self.session_name.text()
        session["session_date"] = self.session_date.date().toString(Qt.ISODate)
        session["session_time"] = self.session_time.time().toString(Qt.ISODate)

        pub.sendMessage("create_session", session=session)

    def clear_subject_fields(self):
        for field in self.subject_fields:
            if field == "birthday":
                getattr(self, field).setDate(QtCore.QDate.currentDate())
            else:
                getattr(self, field).setText("")

    def get_new_subject_id(self):
        pub.sendMessage("get_new_subject_id")

    def update_subject_id(self, subject_id):
        assert type(subject_id) == str
        self.subject_id.setText(subject_id)

    def fill_subject_table(self):
        # Set the id using only the number, so string off the "subject_"
        # Clear any existing contacts
        self.subject_tree.clear()
        # Add the subjects to the subject_tree
        for index, paw in enumerate(range(20)):
            rootItem = QtGui.QTreeWidgetItem(self.subject_tree)
            rootItem.setText(0, str(index))
            rootItem.setText(1, "Blabla")
            rootItem.setText(2, "Bar")
            rootItem.setText(3, str(datetime.date.today()))

        # Select the first item in the contacts tree
        item = self.subject_tree.topLevelItem(0)
        self.subject_tree.setCurrentItem(item)

        # Set the sorting after filling it
        self.subject_tree.sortItems(0)


    # TODO If a subject is selected in the subject_tree, fill in its information in the subject fields
    # TODO Allow for a way to edit the information for a subject and/or session


    def create_toolbar_actions(self):
        self.something_action = gui.create_action(text="&Something",
                                                  shortcut=QtGui.QKeySequence("CTRL+F"),
                                                  icon=QtGui.QIcon(
                                                      os.path.join(os.path.dirname(__file__),
                                                                   "../images/edit_zoom.png")),
                                                  tip="Something",
                                                  checkable=False,
                                                  connection=self.fill_subject_table
        )

        self.create_subject_action = gui.create_action(text="&Create New Subject",
                                                       shortcut=QtGui.QKeySequence("CTRL+S"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/save_icon.png")),
                                                       tip="Create a new subject",
                                                       checkable=False,
                                                       connection=self.create_subject
        )

        self.create_session_action = gui.create_action(text="&Create New Session",
                                                       shortcut=QtGui.QKeySequence("CTRL+SHIFT+S"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/add_session.png")),
                                                       tip="Create a new session",
                                                       checkable=False,
                                                       connection=self.create_session
        )

        self.clear_subject_fields_action = gui.create_action(text="&Clear",
                                                     shortcut=QtGui.QKeySequence("CTRL+Q"),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/cancel_icon.png")),
                                                     tip="Clear all the subject text fields",
                                                     checkable=False,
                                                     connection=self.clear_subject_fields
        )

        self.actions = [self.something_action, self.clear_subject_fields_action,
                        self.create_subject_action, self.create_session_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)

