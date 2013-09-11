import os
import time
import datetime
import logging
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui, utility
from pawlabeling.settings import settings


class MeasurementWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MeasurementWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")
        self.settings = settings.settings
        label_font = self.settings.label_font()

        self.files_tree_label = QtGui.QLabel("Session folder")
        self.files_tree_label.setFont(label_font)

        self.measurement_folder_label = QtGui.QLabel("File path:")
        self.measurement_folder = QtGui.QLineEdit()
        self.measurement_folder.setText(self.settings.measurement_folder())
        self.measurement_folder.textChanged.connect(self.check_measurement_folder)

        self.measurement_folder_button = QtGui.QToolButton()
        self.measurement_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.measurement_folder_button.clicked.connect(self.change_file_location)

        self.measurement_folder_layout = QtGui.QHBoxLayout()
        self.measurement_folder_layout.addWidget(self.measurement_folder)
        self.measurement_folder_layout.addWidget(self.measurement_folder_button)

        self.brand_label = QtGui.QLabel("Brand")
        self.brand = QtGui.QComboBox(self)
        for brand in ["rsscan","zebris","novel","teksan"]:
            self.brand.addItem(brand)

        self.brand.activated.connect(self.change_brand)

        self.model_label = QtGui.QLabel("Model")
        self.model = QtGui.QComboBox(self)
        # TODO load the different models from the config file
        # Then the user can set which systems he/she owns
        for model in ["2m 2nd gen", "1m USB", "0.5m USB"]:
            self.model.addItem(model)

        self.model.activated.connect(self.change_model)

        self.frequency_label = QtGui.QLabel("Frequency")
        self.frequency = QtGui.QComboBox(self)
        for frequency in ["100", "125", "150", "200", "250", "500"]:
            self.frequency.addItem(frequency)

        self.frequency.activated.connect(self.change_frequency)

        # TODO Perhaps add a set to default or something? Though this can/should be done in the settings

        self.brand_model_layout = QtGui.QHBoxLayout()
        self.brand_model_layout.addWidget(self.brand_label)
        self.brand_model_layout.addWidget(self.brand)
        self.brand_model_layout.addWidget(self.model_label)
        self.brand_model_layout.addWidget(self.model)
        self.brand_model_layout.addWidget(self.frequency_label)
        self.brand_model_layout.addWidget(self.frequency)
        self.brand_model_layout.addStretch(1)

        self.files_tree = QtGui.QTreeWidget(self)
        self.files_tree.setColumnCount(3)
        self.files_tree.setHeaderLabels(["Name", "Size", "Date"])
        self.files_tree.header().resizeSection(0, 200)

        self.measurement_tree_label = QtGui.QLabel("Measurements")
        self.measurement_tree_label.setFont(label_font)
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
        self.measurement_layout.addLayout(self.brand_model_layout)
        self.measurement_layout.addWidget(self.files_tree)
        self.measurement_layout.addWidget(self.measurement_tree_label)
        bar_5 = QtGui.QFrame(self)
        bar_5.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.measurement_layout.addWidget(bar_5)
        self.measurement_layout.addWidget(self.measurement_tree)

        self.setLayout(self.measurement_layout)

        pub.subscribe(self.update_measurements_tree, "update_measurements_tree")
        pub.subscribe(self.update_measurement_status, "update_measurement_status")

        self.update_files_tree()

    def update_measurement_status(self, measurements):
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))
        for index in range(self.measurement_tree.topLevelItemCount()):
            item = self.measurement_tree.topLevelItem(index)
            measurement_name = item.text(0)
            if measurement_name in measurements:
                item.setForeground(0, green_brush)

    def update_measurements_tree(self, measurements):
        self.measurement_tree.clear()
        self.measurements = {}
        for index, measurement in enumerate(measurements):
            self.measurements[index] = measurement
            root_item = QtGui.QTreeWidgetItem(self.measurement_tree)
            root_item.setText(0, measurement["measurement_name"])

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item)

    def get_measurements(self, session=None):
        # If we have a different session, clear the tree
        self.measurement_tree.clear()
        pub.sendMessage("get_measurements", measurement={})

    def change_file_location(self, evt=None):
        measurement_folder = self.settings.measurement_folder()
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your measurements",
                                             measurement_folder)
        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        #self.file_dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # TODO Not sure whether I really want to overwrite the default folder, since it might be nested
        # Which makes it hard to use for other sessions, because you have to navigate back up

        # Change where settings.measurement_folder is pointing too
        if self.file_dialog.exec_():
            measurement_folder = self.file_dialog.selectedFiles()[0]

        self.settings.write_value("folders/measurement_folder", measurement_folder)

        self.measurement_folder.setText(measurement_folder)
        # Update the files tree
        self.update_files_tree()

    def check_measurement_folder(self, evt=None):
        measurement_folder = self.measurement_folder.text()
        if os.path.exists(measurement_folder) and os.path.isdir(measurement_folder):
            settings.measurement_folder = measurement_folder
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
        # All measurements from the same session must have the same brands/model/frequency
        brand = settings.brand
        model = settings.model
        frequency = settings.frequency
        for file_name, file_path in self.file_paths.items():
            date_time = time.strftime("%Y-%m-%d %H:%M",time.gmtime(os.path.getctime(file_path))).split(" ")
            # Check if the brands and model have been changed or not
            measurement = {"measurement_name":file_name,
                           "file_path":file_path,
                           "date":date_time[0],
                           "time":date_time[1],
                           "plate":brand,
                           "model":model,
                           "frequency":frequency
            }
            try:
                pub.sendMessage("create_measurement", measurement=measurement)
                # Update the tree after a measurement has been created
                pub.sendMessage("get_measurements", measurement={})
            except settings.MissingIdentifier:
                pass

    def change_brand(self, index):
        brand = self.brand.itemText(index)
        settings.brand = brand
        # Adjust the size in case the text is too big to fit
        self.brand.adjustSize()
        self.logger.info("measurementwidget.change_brand: Brand changed to {}".format(brand))

    def change_model(self, index):
        model = self.model.itemText(index)
        settings.model = model
        self.model.adjustSize()
        self.logger.info("measurementwidget.change_model: Model changed to {}".format(model))

    def change_frequency(self, index):
        frequency = self.frequency.itemText(index)
        # The combobox stores text, so be sure to convert to int!
        settings.frequency = int(frequency)
        self.frequency.adjustSize()
        self.logger.info("measurmentwidget.change_frequency: Frequency changed to {}".format(frequency))