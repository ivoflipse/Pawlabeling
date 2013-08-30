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
from pawlabeling.widgets.database import subjectwidget


class SessionWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SessionWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")

        self.session_label = QtGui.QLabel("Session")
        self.session_label.setFont(parent.font)
        self.session_name_label = QtGui.QLabel("Session Name")
        self.session_date_label = QtGui.QLabel("Session Date")
        self.session_time_label = QtGui.QLabel("Session Time")

        self.session_name = QtGui.QLineEdit()
        self.session_date = QtGui.QDateEdit(QtCore.QDate.currentDate())
        self.session_date.setMinimumDate(QtCore.QDate.currentDate().addYears(-100))
        self.session_date.setMaximumDate(QtCore.QDate.currentDate())
        self.session_date.setDisplayFormat(parent.date_format)
        self.session_time = QtGui.QTimeEdit(QtCore.QTime.currentTime())
        #self.time_format = QtCore.QLocale.system().timeFormat(QtCore.QLocale.ShortFormat)
        self.session_time.setDisplayFormat(u"HH:mm")

        self.session_tree_label = QtGui.QLabel("Sessions")
        self.session_tree_label.setFont(parent.font)
        self.session_tree = QtGui.QTreeWidget(self)
        #self.session_tree.setMinimumWidth(300)
        #self.session_tree.setMaximumWidth(400)
        self.session_tree.setColumnCount(3)
        self.session_tree.setHeaderLabels(["Name", "Date", "Time"])

        self.session_tree.itemActivated.connect(self.put_session)

        self.session_layout = QtGui.QGridLayout()
        self.session_layout.setSpacing(10)
        self.session_layout.addWidget(self.session_name_label, 1, 0)
        self.session_layout.addWidget(self.session_name, 1, 1)
        self.session_layout.addWidget(self.session_date_label, 2, 0)
        self.session_layout.addWidget(self.session_date, 2, 1)
        self.session_layout.addWidget(self.session_time_label, 3, 0)
        self.session_layout.addWidget(self.session_time, 3, 1)

        self.session_tree_layout = QtGui.QVBoxLayout()
        self.session_tree_layout.addWidget(self.session_label)
        bar_3 = QtGui.QFrame(self)
        bar_3.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.session_tree_layout.addWidget(bar_3)
        self.session_tree_layout.addLayout(self.session_layout)
        self.session_tree_layout.addWidget(self.session_tree_label)
        bar_4 = QtGui.QFrame(self)
        bar_4.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.session_tree_layout.addWidget(bar_4)
        self.session_tree_layout.addWidget(self.session_tree)

        self.setLayout(self.session_tree_layout)

        pub.subscribe(self.update_sessions_tree, "update_sessions_tree")
        pub.subscribe(self.get_sessions, "put_subject")

    def create_session(self):
        session = {}
        session["session_name"] = self.session_name.text()
        session["session_date"] = self.session_date.date().toString(Qt.ISODate)
        session["session_time"] = self.session_time.time().toString(u"HH:mm")

        pub.sendMessage("create_session", session=session)
        # After creating a new session, get the updated table
        self.get_sessions()


    def get_session_fields(self):
        session = {}
        session["session_name"] = self.session_name.text()
        session["session_date"] = self.session_date.date().toString(Qt.ISODate)
        session["session_time"] = self.session_time.time().toString(u"HH:mm")  # Qt.ISODate
        return session

    def get_sessions(self, subject=None):
        session = self.get_session_fields()
        pub.sendMessage("get_sessions", session=session)

    def put_session(self, evt=None):
        current_item = self.session_tree.currentItem()
        # Get the index
        index = self.session_tree.indexFromItem(current_item).row()
        session = self.sessions[index]
        pub.sendMessage("put_session", session=session)

    def update_sessions_tree(self, sessions):
        self.session_tree.clear()
        self.sessions = {}
        for index, session in enumerate(sessions):
            self.sessions[index] = session
            rootItem = QtGui.QTreeWidgetItem(self.session_tree)
            rootItem.setText(0, session["session_name"])
            rootItem.setText(1, session["session_date"])
            rootItem.setText(2, session["session_time"])

        item = self.session_tree.topLevelItem(0)
        self.session_tree.setCurrentItem(item)