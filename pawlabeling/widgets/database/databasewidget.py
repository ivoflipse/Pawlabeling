import os
from collections import defaultdict
import logging
import datetime
import numpy as np
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

        self.subject_id_label = QtGui.QLabel("Subject ID")
        self.birthday_label = QtGui.QLabel("Birthday")
        self.first_name_label = QtGui.QLabel("First Name")
        self.last_name_label = QtGui.QLabel("Last Name")
        self.address_label = QtGui.QLabel("Address")
        self.city_label = QtGui.QLabel("City")
        self.phone_label = QtGui.QLabel("Phone")
        self.email_label = QtGui.QLabel("Email")

        self.layout = QtGui.QVBoxLayout()

        self.subject_layout = QtGui.QVBoxLayout()
        self.subject_layout.addWidget(self.subject_tree)

        self.horizontal_layout = QtGui.QHBoxLayout()

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.main_layout.addLayout(self.subject_layout)
        self.setLayout(self.main_layout)


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

        self.actions = [self.something_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)

