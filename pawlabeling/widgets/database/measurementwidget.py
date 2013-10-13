import os
import time
import datetime
import logging
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import io, gui, utility
from pawlabeling.settings import settings
from pawlabeling.models import model

class MeasurementWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MeasurementWidget, self).__init__(parent)

        self.logger = logging.getLogger("logger")
        self.model = model.model
        self.settings = settings.settings
        label_font = self.settings.label_font()

        self.files_tree_label = QtGui.QLabel("Session folder")
        self.files_tree_label.setFont(label_font)

        self.measurement_folder_label = QtGui.QLabel("File path:")
        self.measurement_folder = QtGui.QLineEdit()
        self.measurement_folder.setText(self.model.measurement_folder)
        self.measurement_folder.textChanged.connect(self.check_measurement_folder)

        self.measurement_folder_button = QtGui.QToolButton()
        self.measurement_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.measurement_folder_button.clicked.connect(self.change_file_location)

        self.measurement_up_button = QtGui.QToolButton()
        self.measurement_up_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_up_icon.png")))
        self.measurement_up_button.clicked.connect(self.move_folder_up)

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
        self.plate_layout.addWidget(self.measurement_up_button)
        self.plate_layout.addStretch(1)

        self.files_tree = QtGui.QTreeWidget(self)
        self.files_tree.setColumnCount(4)
        self.files_tree.setHeaderLabels(["","Name", "Size", "Date"])
        self.files_tree.header().resizeSection(0, 200)
        self.files_tree.setColumnWidth(0, 40)
        self.files_tree.itemActivated.connect(self.select_file)

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
        # TODO This workflow seems rather broken
        pub.subscribe(self.update_measurements_tree, "update_measurement_status")
        pub.subscribe(self.update_plates, "update_plates")

        self.update_files_tree()
        self.get_plates()

    def get_plates(self):
        self.model.get_plates()

    def delete_measurement(self):
        current_item = self.measurement_tree.currentItem()
        index = self.measurement_tree.indexFromItem(current_item).row()
        measurement = self.measurements[index]
        self.model.delete_measurement(measurement=measurement)

    def update_plates(self):
        # This sorts the plates by the number in their plate_id
        for plate_id in sorted(self.model.plates, key=lambda x: int(x.split("_")[1])):
            plate = self.model.plates[plate_id]
            self.plate.addItem("{} {}".format(plate.brand, plate.model))

        # Check the settings for which plate to set as default
        plate = self.settings.plate()
        index = self.plate.findText(plate)
        self.plate.setCurrentIndex(index)

    def update_measurements_tree(self):
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        self.measurements = {}
        for index, measurement in enumerate(self.model.measurements.values()):
            self.measurements[index] = measurement
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree)
            measurement_item.setText(0, measurement.measurement_name)

            # If several contacts have been labeled, marked the measurement
            if measurement.processed:
                for idx in xrange(measurement_item.columnCount()):
                    measurement_item.setForeground(idx, green_brush)

        measurement_item = self.measurement_tree.topLevelItem(0)
        self.measurement_tree.setCurrentItem(measurement_item)

    def get_measurements(self):
        # If we have a different session, clear the tree
        self.measurement_tree.clear()
        self.model.get_measurements()

    def change_file_location(self, evt=None):
        # We load the measurement folder from the settings, this is the base folder. Then we select the folder
        # we're interested in and set model.measurement_folder to that value
        measurement_folder = self.settings.measurement_folder()
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your measurements",
                                             measurement_folder)
        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        #self.file_dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # Change where settings.measurement_folder is pointing too
        if self.file_dialog.exec_():
            measurement_folder = self.file_dialog.selectedFiles()[0]

        # I'm no longer overwriting the settings, that wasn't very user friendly
        #self.settings.write_value("folders/measurement_folder", measurement_folder)
        self.model.measurement_folder = measurement_folder

        self.measurement_folder.setText(measurement_folder)
        # Update the files tree
        self.update_files_tree()

    def check_measurement_folder(self, evt=None):
        measurement_folder = self.measurement_folder.text()
        self.model.measurement_folder = measurement_folder
        if os.path.exists(measurement_folder) and os.path.isdir(measurement_folder):
            self.update_files_tree()

    def update_files_tree(self):
        self.files_tree.clear()

        self.file_paths = io.get_file_paths(measurement_folder=self.model.measurement_folder)
        sort_list = []
        for file_name, file_path in self.file_paths.iteritems():
            if not os.path.isfile(file_path):
                sort_list.append((0, file_name))
            else:
                sort_list.append((1, file_name))

        # I want it sorted by type and name
        sort_list = sorted(sort_list, key=lambda x: (x[0], x[1]))

        for file_type, file_name in sort_list:
            file_path = self.file_paths[file_name]
            root_item = QtGui.QTreeWidgetItem(self.files_tree)
            # If its not a measurement, give it a directory icon
            if not file_type:
                root_item.setIcon(0, QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                              "../images/folder_icon.png")))
            else:
                # Give it some paw as an icon
                root_item.setIcon(0, QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                              "../images/paw_icon.png")))
            root_item.setText(1, file_name)
            file_size = os.path.getsize(file_path)
            file_size = utility.humanize_bytes(bytes=file_size, precision=1)
            root_item.setText(2, file_size)
            # This is one messed up format
            creation_date = os.path.getctime(file_path)
            creation_date = time.strftime("%Y-%m-%d", time.gmtime(creation_date))
            # DAMNIT Why can't I use a locale on this?
            root_item.setText(3, creation_date)

    def select_file(self, evt=None):
         # Check if the tree aint empty!
        if not self.files_tree.topLevelItemCount():
            return

        current_item = self.files_tree.currentItem()
        file_name = current_item.text(1)
        file_path = self.file_paths[file_name]
        # Check if its a directory
        if os.path.isdir(file_path):
            # Update the text in self.measurement_folder
            self.measurement_folder.setText(file_path)

    def move_folder_up(self, evt=None):
        measurement_folder = self.measurement_folder.text()
        parent_directory = os.path.dirname(measurement_folder)
        self.measurement_folder.setText(parent_directory)

    def add_measurements(self, evt=None):
        # All measurements from the same session must have the same brands/model/frequency
        plate_text = self.plate.itemText(self.plate.currentIndex())
        index = plate_text.find(" ")
        brand = plate_text[:index]
        model = plate_text[index + 1:]
        plate = self.find_plate(brand=brand, model=model)
        plate_id = plate.plate_id
        frequency = int(self.frequency.itemText(self.frequency.currentIndex()))
        # Initialize a progress bar
        progress = 0
        pub.sendMessage("update_progress", progress=progress)
        # Calculate how much progress we make each step
        total_work =  len(self.file_paths)
        step_work = 100. / total_work

        for file_name, file_path in self.file_paths.iteritems():
            # Only load measurements, so skip directories
            if not os.path.isfile(file_path):
                print file_path
                continue

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
                self.model.create_measurement(measurement=measurement)
                # Update the tree after a measurement has been created
                self.get_measurements()
                # Increment the progress
                progress += step_work
                pub.sendMessage("update_progress", progress=progress)
            except settings.MissingIdentifier:
                pass

        # When we're done, signal we've reached 100%
        progress = 100
        pub.sendMessage("update_progress", progress=progress)

    def find_plate(self, brand, model):
        for plate_id, plate in self.model.plates.iteritems():
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