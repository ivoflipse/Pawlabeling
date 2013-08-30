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
from pawlabeling.widgets.database import subjectwidget, sessionwidget, measurementwidget

class DatabaseWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")

        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder

        self.toolbar = gui.Toolbar(self)
        self.font = QtGui.QFont("Helvetica", 14, QtGui.QFont.Bold)
        self.date_format = QtCore.QLocale.system().dateFormat(QtCore.QLocale.ShortFormat)

        self.subject_widget = subjectwidget.SubjectWidget(self)
        self.session_widget = sessionwidget.SessionWidget(self)
        self.measurement_widget = measurementwidget.MeasurementWidget(self)
        # Create all the toolbar actions
        self.create_toolbar_actions()

        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addWidget(self.subject_widget)
        self.horizontal_layout.addWidget(self.session_widget)
        self.horizontal_layout.addWidget(self.measurement_widget)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

    def create_toolbar_actions(self):
        self.something_action = gui.create_action(text="&Something",
                                                  shortcut=QtGui.QKeySequence("CTRL+F"),
                                                  icon=QtGui.QIcon(
                                                      os.path.join(os.path.dirname(__file__),
                                                                   "../images/edit_zoom.png")),
                                                  tip="Something",
                                                  checkable=False,
                                                  connection=self.subject_widget.get_subjects
        )

        self.create_subject_action = gui.create_action(text="&Create New Subject",
                                                       shortcut=QtGui.QKeySequence("CTRL+S"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/save_icon.png")),
                                                       tip="Create a new subject",
                                                       checkable=False,
                                                       connection=self.subject_widget.create_subject
        )

        self.create_session_action = gui.create_action(text="&Create New Session",
                                                       shortcut=QtGui.QKeySequence("CTRL+SHIFT+S"),
                                                       icon=QtGui.QIcon(
                                                           os.path.join(os.path.dirname(__file__),
                                                                        "../images/add_session.png")),
                                                       tip="Create a new session",
                                                       checkable=False,
                                                       connection=self.session_widget.create_session
        )

        self.clear_subject_fields_action = gui.create_action(text="&Clear",
                                                     shortcut=QtGui.QKeySequence("CTRL+Q"),
                                                     icon=QtGui.QIcon(
                                                         os.path.join(os.path.dirname(__file__),
                                                                      "../images/cancel_icon.png")),
                                                     tip="Clear all the subject text fields",
                                                     checkable=False,
                                                     connection=self.subject_widget.clear_subject_fields
        )

        self.actions = [self.something_action, self.clear_subject_fields_action,
                        self.create_subject_action, self.create_session_action]

        for action in self.actions:
            #action.setShortcutContext(Qt.WindowShortcut)
            self.toolbar.addAction(action)

