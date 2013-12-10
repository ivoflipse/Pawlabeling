import os
import time
import datetime
import logging
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from ...functions import io, gui, utility
from ...settings import settings
from ...models import model

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
                                                                        "../images/folder.png")))
        self.measurement_folder_button.clicked.connect(self.change_file_location)

        self.measurement_up_button = QtGui.QToolButton()
        self.measurement_up_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                    "../images/folder_up.png")))
        self.measurement_up_button.clicked.connect(self.move_folder_up)

        self.measurement_reset_button = QtGui.QToolButton()
        self.measurement_reset_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                       "../images/folder_refresh.png")))
        self.measurement_reset_button.clicked.connect(self.reset_measurement_folder)

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
        # Check the settings for which plate to set as default
        frequency = self.settings.frequency()
        index = self.frequency.findText(frequency)
        self.frequency.setCurrentIndex(index)

        self.plate_layout = QtGui.QHBoxLayout()
        self.plate_layout.addWidget(self.plate_label)
        self.plate_layout.addWidget(self.plate)
        self.plate_layout.addWidget(self.frequency_label)
        self.plate_layout.addWidget(self.frequency)
        self.plate_layout.addWidget(self.measurement_up_button)
        self.plate_layout.addWidget(self.measurement_reset_button)
        self.plate_layout.addStretch(1)

        self.files_tree = QtGui.QTreeWidget(self)
        self.files_tree.setColumnCount(4)
        self.files_tree.setHeaderLabels(["","Name", "Size", "Date"])
        self.files_tree.header().resizeSection(0, 200)
        self.files_tree.setColumnWidth(0, 40)
        self.files_tree.setColumnWidth(1, 130)
        self.files_tree.itemActivated.connect(self.select_file)
        self.files_tree.setSortingEnabled(True)

        self.measurement_tree_label = QtGui.QLabel("Measurements")
        self.measurement_tree_label.setFont(label_font)
        self.measurement_tree = QtGui.QTreeWidget(self)
        #self.measurement_tree.setMinimumWidth(300)
        self.measurement_tree.setColumnCount(1)
        self.measurement_tree.setHeaderLabels(["Name"])
        self.measurement_tree.setSortingEnabled(True)

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

        pub.subscribe(self.update_measurements_tree, "get_measurements")
        pub.subscribe(self.update_plates, "get_plates")
        pub.subscribe(self.changed_settings, "changed_settings")

        self.update_files_tree()
        self.get_plates()

    def get_plates(self):
        self.model.get_plates()

    def delete_measurement(self):
        current_item = self.measurement_tree.currentItem()
        measurement_id = current_item.text(1)
        measurement = self.model.measurements[measurement_id]
        message = "Are you sure you want to delete measurement: {}?".format(measurement.measurement_name)
        self.dialog = gui.Dialog(message=message, title="Delete measurement?", parent=self)
        response = self.dialog.exec_()
        if response:
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

    def changed_settings(self):
        self.update_plates()

    def update_measurements_tree(self):
        self.measurement_tree.clear()
        # Create a green brush for coloring stored results
        green_brush = QtGui.QBrush(QtGui.QColor(46, 139, 87))

        for index, measurement in enumerate(self.model.measurements.values()):
            measurement_item = QtGui.QTreeWidgetItem(self.measurement_tree)
            measurement_item.setText(0, measurement.measurement_name)
            measurement_item.setText(1, measurement.measurement_id)

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
        for file_name, file_path in self.file_paths.iteritems():
            file_path = self.file_paths[file_name]
            root_item = QtGui.QTreeWidgetItem(self.files_tree)
            # If its not a measurement, give it a directory icon
            if not os.path.isfile(file_path):
                root_item.setIcon(0, QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                              "../images/folder.png")))
            else:
                # Give it some paw as an icon
                root_item.setIcon(0, QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                              "../images/paw.png")))
            root_item.setText(1, file_name)
            file_size = os.path.getsize(file_path)
            file_size = utility.humanize_bytes(bytes=file_size, precision=1)
            root_item.setText(2, file_size)
            # This is one messed up format
            creation_date = os.path.getctime(file_path)
            creation_date = time.strftime("%Y-%m-%d", time.gmtime(creation_date))
            # DAMNIT Why can't I use a locale on this?
            root_item.setText(3, creation_date)
            root_item.setText(4, file_path)

    def select_file(self):
         # Check if the tree aint empty!
        if not self.files_tree.topLevelItemCount():
            return

        current_item = self.files_tree.currentItem()
        file_path = current_item.text(4)
        # Check if its a directory
        if os.path.isdir(file_path):
            # Update the text in self.measurement_folder
            self.measurement_folder.setText(file_path)

    def move_folder_up(self):
        measurement_folder = self.measurement_folder.text()
        parent_directory = os.path.dirname(measurement_folder)
        self.measurement_folder.setText(parent_directory)

    def reset_measurement_folder(self):
        measurement_folder = self.settings.measurement_folder()
        self.measurement_folder.setText(measurement_folder)

    # TODO Check whether there's even a session selected at the moment...
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

        # Make sure the model reloads the session
        self.model.put_session(session=self.model.sessions[self.model.session_id])

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