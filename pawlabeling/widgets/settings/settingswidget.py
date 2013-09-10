import sys
import os
import logging
from collections import defaultdict
from PySide import QtGui, QtCore
from pubsub import pub
from pawlabeling.settings import settings
from pawlabeling.functions import gui


class SettingsWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SettingsWidget, self).__init__(parent)

        # Set up the logger
        self.logger = logging.getLogger("logger")
        self.settings = settings.settings
        label_font = self.settings.label_font()

        self.toolbar = gui.Toolbar(self)

        self.settings_label = QtGui.QLabel("Settings")
        self.settings_label.setFont(label_font)

        self.measurement_folder_label = QtGui.QLabel("Measurements folder")
        self.measurement_folder = QtGui.QLineEdit()
        self.measurement_folder_button = QtGui.QToolButton()
        self.measurement_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.measurement_folder_button.clicked.connect(self.change_measurement_folder)

        self.database_folder_label = QtGui.QLabel("Database folder")
        self.database_folder = QtGui.QLineEdit()
        self.database_folder_button = QtGui.QToolButton()
        self.database_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.database_folder_button.clicked.connect(self.change_database_folder)


        self.database_file_label = QtGui.QLabel("Database file")
        self.database_file = QtGui.QLineEdit()

        self.left_front_label = QtGui.QLabel("Left Front Shortcut")
        self.left_front = QtGui.QLineEdit()

        self.left_hind_label = QtGui.QLabel("Left Hind Shortcut")
        self.left_hind = QtGui.QLineEdit()

        self.right_front_label = QtGui.QLabel("Right Front Shortcut")
        self.right_front = QtGui.QLineEdit()

        self.right_hind_label = QtGui.QLabel("Right Hind Shortcut")
        self.right_hind = QtGui.QLineEdit()

        self.interpolation_entire_plate_label = QtGui.QLabel("Interpolation: Entire Plate")
        self.interpolation_entire_plate = QtGui.QLineEdit()

        self.interpolation_contact_widgets_label = QtGui.QLabel("Interpolation: Contact Widgets")
        self.interpolation_contact_widgets = QtGui.QLineEdit()

        self.interpolation_results_label = QtGui.QLabel("Interpolation: Results")
        self.interpolation_results  = QtGui.QLineEdit()

        self.start_force_percentage_label = QtGui.QLabel("Start Force %")
        self.start_force_percentage = QtGui.QLineEdit()

        self.end_force_percentage_label = QtGui.QLabel("End Force %")
        self.end_force_percentage = QtGui.QLineEdit()

        self.tracking_temporal_label = QtGui.QLabel("Tracking Temporal Threshold")
        self.tracking_temporal = QtGui.QLineEdit()

        self.tracking_spatial_label = QtGui.QLabel("Tracking Spatial Threshold")
        self.tracking_spatial = QtGui.QLineEdit()

        self.tracking_surface_label = QtGui.QLabel("Tracking Surface Threshold")
        self.tracking_surface = QtGui.QLineEdit()

        self.update_fields()

        self.widgets = [["measurement_folder_label","measurement_folder", "measurement_folder_button"],
                        ["database_folder_label", "database_folder", "database_folder_button"],
                        ["database_file_label", "database_file"],
                        ["left_front_label", "left_front", "", "right_front_label", "right_front"],
                        ["left_hind_label", "left_hind", "", "right_hind_label", "right_hind"],
                        ["interpolation_entire_plate_label", "interpolation_entire_plate", "",
                        "interpolation_contact_widgets_label", "interpolation_contact_widgets", "",
                        "interpolation_results_label", "interpolation_results"],
                        ["start_force_percentage_label", "start_force_percentage", "",
                         "end_force_percentage_label", "end_force_percentage", ""],
                        ["tracking_temporal_label", "tracking_temporal", "",
                         "tracking_spatial_label", "tracking_spatial", "",
                         "tracking_surface_label", "tracking_surface", ""]
        ]

        self.settings_layout = QtGui.QGridLayout()
        self.settings_layout.setSpacing(10)

        # This neatly fills the QGridLayout for us
        for row, widgets in enumerate(self.widgets):
            for column, widget_name in enumerate(widgets):
                if widget_name:
                    widget = getattr(self, widget_name)
                    self.settings_layout.addWidget(widget, row, column)


        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.settings_label)
        bar_1 = QtGui.QFrame(self)
        bar_1.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.main_layout.addWidget(bar_1)
        self.main_layout.addLayout(self.settings_layout)
        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)

        self.create_toolbar_actions()

        #pub.subscribe(self.change_status, "update_statusbar")
        #pub.subscribe(self.launch_message_box, "message_box")

    def update_fields(self):
        """
        This function is called by __init__ and when the tab is switched to settings.
        That way it'll always display the current values of the settings
        """
        self.measurement_folder.setText(self.settings.measurement_folder())
        self.database_folder.setText(self.settings.database_folder())
        self.database_file.setText(self.settings.database_file())

        self.left_front.setText(self.settings.left_front().toString())
        self.left_hind.setText(self.settings.left_hind().toString())
        self.right_front.setText(self.settings.right_front().toString())
        self.right_hind.setText(self.settings.right_hind().toString())

        self.interpolation_entire_plate.setText(str(self.settings.interpolation_entire_plate()))
        self.interpolation_contact_widgets.setText(str(self.settings.interpolation_contact_widgets()))
        self.interpolation_results.setText(str(self.settings.interpolation_results()))
        self.start_force_percentage.setText(str(self.settings.start_force_percentage()))
        self.end_force_percentage.setText(str(self.settings.end_force_percentage()))
        self.tracking_temporal.setText(str(self.settings.tracking_temporal()))
        self.tracking_spatial.setText(str(self.settings.tracking_spatial()))
        self.tracking_surface.setText(str(self.settings.tracking_surface()))

    def save_settings(self, evt=None):
        """
        Store the changes to the widgets to the settings.ini file
        This function should probably do some validation
        """
        settings_dict = self.settings.read_settings()
        for key, nested in settings_dict.items():
            # This will help skip settings we don't change anyway
            if key not in self.settings.lookup_table:
                del settings_dict[key]
                break

            for nested_key, old_value in nested.items():
                if type(nested_key) not in [str, unicode]:
                    break

                if hasattr(self, nested_key):
                    new_value = getattr(self, nested_key).text()
                    if type(old_value) == int:
                        new_value = int(new_value)
                    if type(old_value) == float:
                        new_value = float(new_value)
                    if type(old_value) == QtGui.QKeySequence:
                        new_value = QtGui.QKeySequence.fromString(new_value)
                    if type(old_value) == bool:
                        new_value = bool(new_value)
                        print new_value
                    if old_value != new_value:
                        settings_dict[key][nested_key] = new_value

        self.settings.save_settings(settings_dict)

        # Notify the rest of the application that the settings have changed
        # TODO: changes here should propagate to the rest of the application (like the database screen)
        pub.sendMessage("changed_settings")

    def change_measurement_folder(self, evt=None):
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

        #self.settings.write_value("folders/measurement_folder", measurement_folder)
        self.measurement_folder.setText(measurement_folder)

    def change_database_folder(self, evt=None):
        database_folder = self.settings.database_folder()
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your database",
                                             database_folder)

        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # Change where settings.measurement_folder is pointing too
        if self.file_dialog.exec_():
            database_folder = self.file_dialog.selectedFiles()[0]

        #self.settings.write_value("folders/database_folder", database_folder)
        self.database_folder.setText(database_folder)

    def create_toolbar_actions(self):
        self.save_settings_action = gui.create_action(text="&Save Settings",
                                                        shortcut=QtGui.QKeySequence("CTRL+S"),
                                                        icon=QtGui.QIcon(
                                                            os.path.join(os.path.dirname(__file__),
                                                                         "../images/save_icon.png")),
                                                        tip="Save settings",
                                                        checkable=False,
                                                        connection=self.save_settings
        )

        self.actions = [self.save_settings_action]

        for action in self.actions:
            self.toolbar.addAction(action)