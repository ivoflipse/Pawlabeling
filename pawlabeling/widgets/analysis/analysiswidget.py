from collections import defaultdict
import os
import logging
from PySide import QtGui
from PySide.QtCore import Qt
import numpy as np
from pubsub import pub
from ...functions import gui, io
from ...settings import settings
from ...widgets.analysis import resultswidget
from ...models import model
from ...widgets import measurementtree

class AnalysisWidget(QtGui.QTabWidget):
    def __init__(self, parent):
        super(AnalysisWidget, self).__init__(parent)
        # Initialize num_frames, in case measurements aren't loaded
        self.frame = 0
        self.n_max = 0
        self.subject_name = ""
        self.model = model.model

        self.colors = settings.settings.colors
        self.contact_dict = settings.settings.contact_dict
        self.average_toggle = False

        self.toolbar = gui.Toolbar(self)

        self.measurement_tree = measurementtree.MeasurementTree()
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
        pub.sendMessage("model_filter_outliers")

    def put_contact(self):
        self.set_max_length()

    def show_average_results(self):
        pub.sendMessage("model_show_average_results")
        # Not particularly elegant that this has to be called here
        self.set_max_length()

    def set_max_length(self):
        if self.results_widget.current_widget == self.results_widget.gait_diagram_widget:
            self.slider.setMaximum(self.model.measurement.number_of_frames)
            return
        elif self.average_toggle:
            self.max_length = self.model.max_length
            self.slider.setMaximum(self.max_length)
            return
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