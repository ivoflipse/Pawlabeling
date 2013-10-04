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
        self.colors = self.settings.colors()
        self.contact_dict = self.settings.contact_dict()

        self.toolbar = gui.Toolbar(self)

        # Create a list widget
        self.measurement_tree = QtGui.QTreeWidget(self)
        self.measurement_tree.setMaximumWidth(300)
        self.measurement_tree.setMinimumWidth(300)
        #self.measurement_tree.setMaximumHeight(200)
        self.measurement_tree.setColumnCount(5)
        self.measurement_tree.setHeaderLabels(["Name", "Label", "Length", "Surface", "Force"])
        self.measurement_tree.itemActivated.connect(self.item_activated)

        # Set the widths of the columns
        for column in xrange(self.measurement_tree.columnCount()):
            self.measurement_tree.setColumnWidth(column, 55)

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
        self.horizontal_layout.addLayout(self.layout)
        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addLayout(self.horizontal_layout)
        self.setLayout(self.main_layout)

        self.subscribe()

        self.create_toolbar_actions()

    def subscribe(self):
        pub.subscribe(self.update_measurements_tree, "update_measurement_status")

    def unsubscribe(self):
        pub.unsubscribe(self.update_measurements_tree, "update_measurement_status")

    def item_activated(self):
        # Check if the tree aint empty!
        if not self.measurement_tree.topLevelItemCount():
            return

        current_item = self.measurement_tree.currentItem()
        if current_item.parent():
            self.put_contact()
        else:
            self.put_measurement()

    def get_current_measurement_item(self):
        return self.measurement_tree.topLevelItem(self.current_measurement_index)

    def update_measurements_tree(self):
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        self.measurements = {}
        for index, measurement in enumerate(self.model.measurements.values()):
            self.measurements[index] = measurement
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree, [measurement])
            measurement_item.setText(0, measurement.measurement_name)
            measurement_item.setFirstColumnSpanned(True)
            for contact in self.model.contacts[measurement.measurement_name]:
                if contact.length > self.max_length:
                    self.max_length = contact.length

                contact_item = QtGui.QTreeWidgetItem(measurement_item)
                contact_item.setText(0, str(contact.contact_id))
                contact_item.setText(1, self.contact_dict[contact.contact_label])
                contact_item.setText(2, str(contact.length))  # Sets the frame count
                max_surface = np.max(contact.surface_over_time)
                contact_item.setText(3, str(int(max_surface)))
                max_force = np.max(contact.force_over_time)
                contact_item.setText(4, str(int(max_force)))

                for idx in xrange(contact_item.columnCount()):
                    color = self.colors[contact.contact_label]
                    color.setAlphaF(0.5)
                    contact_item.setBackground(idx, color)

            # If several contacts have been labeled, marked the measurement
            if measurement.processed:
                for idx in xrange(measurement_item.columnCount()):
                    measurement_item.setForeground(idx, green_brush)

        # Initialize the current contact index, which we'll need for keep track of the labeling
        self.current_contact_index = 0
        self.current_measurement_index = 0
        measurement_item = self.measurement_tree.topLevelItem(self.current_measurement_index)
        self.measurement_tree.setCurrentItem(measurement_item, True)

        # Update the slider's max value
        self.slider.setMaximum(self.max_length)


    def change_frame(self, frame):
        self.slider_text.setText("Frame: {}".format(frame))
        self.frame = frame
        pub.sendMessage("analysis.change_frame", frame=self.frame)

    def filter_outliers(self, event=None):
        self.outlier_toggle = not self.outlier_toggle
        pub.sendMessage("filter_outliers", toggle=self.outlier_toggle)

    def put_measurement(self):
        current_item = self.measurement_tree.currentItem()
        # Notify the model to update the subject_name + measurement_name if necessary
        measurement_name = current_item.text(0)
        measurement = {"measurement_name": measurement_name}
        self.model.put_measurement(measurement=measurement)

    def put_contact(self):
        current_item = self.measurement_tree.currentItem()
        contact_id = current_item.text(0)
        self.model.put_contact(contact_id=contact_id)

    # TODO This needs to be re-enabled somehow
    # def calculate_results(self):
    #     self.model.calculate_results()
    #     pub.sendMessage("calculate_results")

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