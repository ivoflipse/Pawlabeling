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

        self.plate_label = QtGui.QLabel("Plate")
        self.plate = QtGui.QComboBox(self)
        self.plate.activated.connect(self.change_plate)

        self.frequency_label = QtGui.QLabel("Frequency")
        self.frequency = QtGui.QComboBox(self)
        for frequency in ["100", "125", "150", "200", "250", "500"]:
            self.frequency.addItem(frequency)
        self.frequency.activated.connect(self.change_frequency)

        self.plate_layout = QtGui.QHBoxLayout()
        self.plate_layout.addWidget(self.plate_label)
        self.plate_layout.addWidget(self.plate)
        self.plate_layout.addWidget(self.frequency_label)
        self.plate_layout.addWidget(self.frequency)
        self.plate_layout.addStretch(1)

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
        self.measurement_layout.addLayout(self.plate_layout)
        self.measurement_layout.addWidget(self.files_tree)
        self.measurement_layout.addWidget(self.measurement_tree_label)
        bar_5 = QtGui.QFrame(self)
        bar_5.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.measurement_layout.addWidget(bar_5)
        self.measurement_layout.addWidget(self.measurement_tree)

        self.setLayout(self.measurement_layout)

        pub.subscribe(self.update_measurements_tree, "update_measurements_tree")
        pub.subscribe(self.update_measurement_status, "update_measurement_status")
        pub.subscribe(self.update_plates, "update_plates")

        self.update_files_tree()
        self.get_plates()

    def get_plates(self):
        pub.sendMessage("get_plates")

    def delete_measurement(self):
        current_item = self.measurement_tree.currentItem()
        index = self.measurement_tree.indexFromItem(current_item).row()
        measurement = self.measurements[index]
        pub.sendMessage("delete_measurement", measurement=measurement)

    def update_plates(self, plates):
        self.plates = plates
        # This sorts the plates by the number in their plate_id
        for plate_id in sorted(self.plates, key=lambda x: int(x.split("_")[1])):
            plate = self.plates[plate_id]
            self.plate.addItem("{} {}".format(plate.brand, plate.model))

        # Check the settings for which plate to set as default
        plate = self.settings.plate()
        index = self.plate.findText(plate)
        self.plate.setCurrentIndex(index)

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
        for index, measurement in enumerate(measurements.values()):
            self.measurements[index] = measurement
            root_item = QtGui.QTreeWidgetItem(self.measurement_tree)
            root_item.setText(0, measurement.measurement_name)

        item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(item)

    def get_measurements(self, session=None):
        # If we have a different session, clear the tree
        self.measurement_tree.clear()
        pub.sendMessage("get_measurements")

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
        plate_text = self.plate.itemText(self.plate.currentIndex())
        index = plate_text.find(" ")
        brand = plate_text[:index]
        model = plate_text[index + 1:]
        plate = self.find_plate(brand=brand, model=model)
        plate_id = plate.plate_id
        frequency = int(self.frequency.itemText(self.frequency.currentIndex()))
        for file_name, file_path in self.file_paths.items():
            date_time = time.strftime("%Y-%m-%d %H:%M", time.gmtime(os.path.getctime(file_path))).split(" ")
            # Check if the brands and model have been changed or not
            measurement = {"measurement_name": file_name,
                           "file_path": file_path,
                           "date": date_time[0],
                           "time": date_time[1],
                           "plate_id": plate_id,
                           "frequency": frequency
            }
            try:
                pub.sendMessage("create_measurement", measurement=measurement)
                # Update the tree after a measurement has been created
                pub.sendMessage("get_measurements")
            except settings.MissingIdentifier:
                pass

    def find_plate(self, brand, model):
        for plate_id, plate in self.plates.items():
            if plate.brand == brand and plate.model == model:
                return plate

    def change_plate(self, index):
        plate = self.plate.itemText(index)
        # Write the currently select plate to the settings
        self.settings.write_value("plate/plate", plate)
        # Adjust the size in case the text is too big to fit
        self.plate.adjustSize()
        self.logger.info("measurementwidget.change_plate: Plate changed to {}".format(plate))

    def change_frequency(self, index):
        frequency = self.frequency.itemText(index)
        self.frequency.adjustSize()
        self.logger.info("measurmentwidget.change_frequency: Frequency changed to {}".format(frequency))