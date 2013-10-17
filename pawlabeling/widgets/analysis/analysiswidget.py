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
from pawlabeling.models import model
from pawlabeling.widgets import measurementtree

class AnalysisWidget(QtGui.QTabWidget):
    def __init__(self, parent):
        super(AnalysisWidget, self).__init__(parent)
        # Initialize num_frames, in case measurements aren't loaded
        self.frame = 0
        self.n_max = 0
        self.subject_name = ""
        self.outlier_toggle = False
        self.logger = logging.getLogger("logger")
        self.model = model.model

        self.settings = settings.settings
        self.colors = self.settings.colors
        self.contact_dict = self.settings.contact_dict
        self.average_toggle = False

        self.toolbar = gui.Toolbar(self)

        self.measurement_tree = measurementtree.get_measurement_tree()
        self.results_widget = resultswidget.ResultsWidget(self)

        # Create a slider
        self.slider = QtGui.QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(-1)
        self.max_length = 0
        self.slider.setMaximum(self.max_length)
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
        self.horizontal_layout = QtGui.QHBoxLayout()
        self.horizontal_layout.addLayout(self.vertical_layout)
        self.horizontal_layout.addLayout(self.layout, stretch=1)
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

        self.create_toolbar_actions()
        pub.subscribe(self.put_contact, "put_contact")

    def change_frame(self, frame):
        self.slider_text.setText("Frame: {}".format(frame))
        self.frame = frame
        pub.sendMessage("analysis.change_frame", frame=self.frame)

    def filter_outliers(self, event=None):
        self.outlier_toggle = not self.outlier_toggle
        pub.sendMessage("filter_outliers", toggle=self.outlier_toggle)

    # TODO This will be problematic if called before the function that actually puts the contact
    def put_contact(self):
        self.set_max_length()

    def show_average_results(self):
        self.average_toggle = not self.average_toggle
        pub.sendMessage("show_average_results", toggle=self.average_toggle)
        self.set_max_length()

    def set_max_length(self):
        if self.average_toggle:
            self.slider.setMaximum(self.max_length)
        else:
            max_length = 0
            for contact in self.model.selected_contacts.values():
                if contact.length > max_length:
                    max_length = contact.length
            self.slider.setMaximum(max_length)

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
                                                                              "../images/force_graph.png")),
                                                             tip="Switch to average results",
                                                             checkable=True,
                                                             connection=self.show_average_results
        )

        self.actions = [self.filter_outliers_action, self.show_average_results_action,
                        "separator"]

        for action in self.actions:
            if action == "separator":
                self.toolbar.addSeparator()
            else:
                self.toolbar.addAction(action)