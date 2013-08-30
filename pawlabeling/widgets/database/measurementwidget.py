import os
import time
import datetime
import logging
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui, utility
from pawlabeling.settings import configuration


class MeasurementWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MeasurementWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")
        self.date_format = parent.date_format

        self.files_tree_label = QtGui.QLabel("Files")
        self.files_tree_label.setFont(parent.font)
        self.files_tree = QtGui.QTreeWidget(self)
        self.files_tree.setColumnCount(3)
        self.files_tree.setHeaderLabels(["Name", "Size", "Date"])
        self.files_tree.header().resizeSection(0, 200)

        self.measurement_tree_label = QtGui.QLabel("Measurements")
        self.measurement_tree_label.setFont(parent.font)
        self.measurement_tree = QtGui.QTreeWidget(self)
        #self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabels(["Name"])

        self.measurement_layout = QtGui.QVBoxLayout()
        self.measurement_layout.addWidget(self.files_tree_label)
        bar_6 = QtGui.QFrame(self)
        bar_6.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.measurement_layout.addWidget(bar_6)
        self.measurement_layout.addWidget(self.files_tree)
        self.measurement_layout.addWidget(self.measurement_tree_label)
        bar_5 = QtGui.QFrame(self)
        bar_5.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.measurement_layout.addWidget(bar_5)
        self.measurement_layout.addWidget(self.measurement_tree)

        self.setLayout(self.measurement_layout)

        pub.subscribe(self.update_measurement_tree, "update_measurement_tree")
        pub.subscribe(self.get_measurements, "put_sessions")

        self.update_files_tree()

    def change_file_location(self, evt=None):
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your measurements",
                                             configuration.measurement_folder)
        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        #self.file_dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # Store the default in case we don't make a change
        file_name = configuration.measurement_folder
        # Change where configuration.measurement_folder is pointing too
        if self.file_dialog.exec_():
            file_name = self.file_dialog.selectedFiles()[0]

        # TODO instead of overwriting measurement_folder, add a temp variable that's used by the IO module too
        # Then change that, so we always keep our 'default' measurements_folder
        configuration.measurement_folder = file_name
        # Update the files tree
        self.update_files_tree()


    def update_files_tree(self):
        self.files_tree.clear()

        self.file_paths = io.get_file_paths()
        for file_path in self.file_paths.values():
            root_item = QtGui.QTreeWidgetItem(self.files_tree)
            file_name = os.path.basename(file_path)
            root_item.setText(0, file_name)
            file_size = os.path.getsize(file_path)
            file_size = utility.humanize_bytes(bytes=file_size, precision=1)
            root_item.setText(1, file_size)
            # This is one messed up format
            creation_date = os.path.getctime(file_path)
            creation_date = time.strftime("%Y-%m-%d", time.gmtime(creation_date))
            # DAMNIT Why can't I use a locale on this?
            root_item.setText(2, creation_date)


    def update_measurement_tree(self, measurements):
        self.measurement_tree.clear()
        self.measurements = {}
        for index, measurement in enumerate(measurements):
            self.measurements[index] = measurement
            root_item = QtGui.QTreeWidgetItem(self.measurement_tree)
            root_item.setText(0, measurement["measurement_name"])

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item)

    def get_measurements(self, session=None):
        pub.sendMessage("get_measurements", measurement={})