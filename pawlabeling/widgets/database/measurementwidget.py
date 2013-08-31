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

        self.files_tree_label = QtGui.QLabel("Session folder")
        self.files_tree_label.setFont(parent.font)

        self.measurement_folder_label = QtGui.QLabel("File path:")
        self.measurement_folder = QtGui.QLineEdit()
        self.measurement_folder.setText(configuration.measurement_folder)
        self.measurement_folder.textChanged.connect(self.check_measurement_folder)

        self.measurement_folder_button = QtGui.QToolButton()
        self.measurement_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.measurement_folder_button.clicked.connect(self.change_file_location)

        self.measurement_folder_layout = QtGui.QHBoxLayout()
        self.measurement_folder_layout.addWidget(self.measurement_folder)
        self.measurement_folder_layout.addWidget(self.measurement_folder_button)

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
        self.measurement_layout.addLayout(self.measurement_folder_layout)
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
        self.measurement_folder.setText(file_name)
        # Update the files tree
        self.update_files_tree()

    def check_measurement_folder(self, evt=None):
        measurement_folder = self.measurement_folder.text()
        if os.path.exists(measurement_folder) and os.path.isdir(measurement_folder):
            configuration.measurement_folder = measurement_folder
            self.update_files_tree()

    def update_files_tree(self):
        self.files_tree.clear()

        self.file_paths = io.get_file_paths()
        for file_name, file_path in self.file_paths.items():
            root_item = QtGui.QTreeWidgetItem(self.files_tree)
            root_item.setText(0, file_name)
            file_size = os.path.getsize(file_path)
            file_size = utility.humanize_bytes(bytes=file_size, precision=1)
            root_item.setText(1, file_size)
            # This is one messed up format
            creation_date = os.path.getctime(file_path)
            creation_date = time.strftime("%Y-%m-%d", time.gmtime(creation_date))
            # DAMNIT Why can't I use a locale on this?
            root_item.setText(2, creation_date)

    def add_measurements(self, evt=None):
        """
            measurement_id = tables.StringCol(64)
            session_id = tables.StringCol(64)
            subject_id = tables.StringCol(64)
            measurement_name = tables.StringCol(64)
            number_of_frames = tables.UInt32Col()
            number_of_rows = tables.UInt32Col()
            number_of_cols = tables.UInt32Col()
            measurement_frequency = tables.UInt32Col()
            orientation = tables.BoolCol()
            maximum_value = tables.Float32Col()
            brand = tables.StringCol(32)
            model = tables.StringCol(32)
            date = tables.StringCol(32)
            time = tables.StringCol(32)
        """
        for file_name, file_path in self.file_paths.items():
            date_time = time.strftime("%Y-%m-%d %H:%M",time.gmtime(os.path.getctime(file_path))).split(" ")
            brand = configuration.brand
            model = configuration.model
            # Check if the brand and model have been changed or not
            measurement = {"measurement_name":file_name,
                           "file_path":file_path,
                           "date":date_time[0],
                           "time":date_time[1],
                           "brand":brand,
                           "model":model}
            pub.sendMessage("create_measurement", measurement=measurement)
            # Update the tree after a measurement has been created
            pub.sendMessage("get_measurements", measurement={})

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