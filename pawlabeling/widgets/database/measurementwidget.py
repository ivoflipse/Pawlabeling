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

class MeasurementWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MeasurementWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")

        self.measurement_tree_label = QtGui.QLabel("Measurements")
        self.measurement_tree_label.setFont(parent.font)
        self.measurement_tree = QtGui.QTreeWidget(self)
        #self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabels(["Name"])

        self.measurement_layout = QtGui.QVBoxLayout()
        self.measurement_layout.addWidget(self.measurement_tree_label)
        bar_5 = QtGui.QFrame(self)
        bar_5.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.measurement_layout.addWidget(bar_5)
        self.measurement_layout.addWidget(self.measurement_tree)

        self.setLayout(self.measurement_layout)

        pub.subscribe(self.update_measurement_tree, "update_measurement_tree")
        pub.subscribe(self.get_measurements, "put_sessions")

    def update_measurement_tree(self, measurements):
        self.measurement_tree.clear()
        self.measurements = {}
        for index, measurement in enumerate(measurements):
            self.measurements[index] = measurement
            rootItem = QtGui.QTreeWidgetItem(self.measurement_tree)
            rootItem.setText(0, measurement["measurement_name"])

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item)

    def get_measurements(self, session=None):
        pub.sendMessage("get_measurements", measurement={})