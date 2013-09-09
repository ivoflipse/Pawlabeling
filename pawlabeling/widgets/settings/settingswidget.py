import sys
import os
from PySide import QtGui, QtCore
from pubsub import pub
from pawlabeling.configuration import configuration
from pawlabeling.functions import gui


class SettingsWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SettingsWidget, self).__init__(parent)

        # Set up the logger
        self.logger = configuration.setup_logging()

        self.toolbar = gui.Toolbar(self)

        self.settings_label = QtGui.QLabel("Settings")
        self.settings_label.setFont(configuration.label_font)

        self.measurement_folder_label = QtGui.QLabel("Measurements folder")
        self.measurement_folder = QtGui.QLineEdit()
        self.measurement_folder.setText(configuration.measurement_folder)
        self.measurement_folder_button = QtGui.QToolButton()
        self.measurement_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.measurement_folder_button.clicked.connect(self.change_measurement_folder)

        self.database_folder_label = QtGui.QLabel("Database folder")
        self.database_folder = QtGui.QLineEdit()
        self.database_folder.setText(configuration.database_folder)
        self.database_folder_button = QtGui.QToolButton()
        self.database_folder_button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                        "../images/folder_icon.png")))
        self.database_folder_button.clicked.connect(self.change_database_folder)


        self.database_file_label = QtGui.QLabel("Database file")
        self.database_file = QtGui.QLineEdit()
        self.database_file.setText(configuration.database_file)

        self.left_front_label = QtGui.QLabel("Left Front Shortcut")
        self.left_front = QtGui.QLineEdit()
        self.left_front.setText(configuration.shortcut_strings["left_front"])

        self.left_hind_label = QtGui.QLabel("Left Hind Shortcut")
        self.left_hind = QtGui.QLineEdit()
        self.left_hind.setText(configuration.shortcut_strings["left_hind"])

        self.right_front_label = QtGui.QLabel("Right Front Shortcut")
        self.right_front = QtGui.QLineEdit()
        self.right_front.setText(configuration.shortcut_strings["right_front"])

        self.right_hind_label = QtGui.QLabel("Right Hind Shortcut")
        self.right_hind = QtGui.QLineEdit()
        self.right_hind.setText(configuration.shortcut_strings["right_hind"])

        self.interpolation_entire_plate_label = QtGui.QLabel("Interpolation: Entire Plate")
        self.interpolation_entire_plate = QtGui.QLineEdit()
        self.interpolation_entire_plate.setText(str(configuration.interpolation_entire_plate))

        self.interpolation_contact_widgets_label = QtGui.QLabel("Interpolation: Contact Widgets")
        self.interpolation_contact_widgets = QtGui.QLineEdit()
        self.interpolation_contact_widgets.setText(str(configuration.interpolation_contact_widgets))

        self.interpolation_results_label = QtGui.QLabel("Interpolation: Results")
        self.interpolation_results  = QtGui.QLineEdit()
        self.interpolation_results.setText(str(configuration.interpolation_results))

        self.start_force_percentage_label = QtGui.QLabel("Start Force %")
        self.start_force_percentage = QtGui.QLineEdit()
        self.start_force_percentage.setText(str(configuration.start_force_percentage))

        self.end_force_percentage_label = QtGui.QLabel("End Force %")
        self.end_force_percentage = QtGui.QLineEdit()
        self.end_force_percentage.setText(str(configuration.end_force_percentage))

        self.tracking_temporal_label = QtGui.QLabel("Tracking Temporal Threshold")
        self.tracking_temporal = QtGui.QLineEdit()
        self.tracking_temporal.setText(str(configuration.tracking_temporal))

        self.tracking_spatial_label = QtGui.QLabel("Tracking Spatial Threshold")
        self.tracking_spatial = QtGui.QLineEdit()
        self.tracking_spatial.setText(str(configuration.tracking_spatial))

        self.tracking_surface_label = QtGui.QLabel("Tracking Surface Threshold")
        self.tracking_surface = QtGui.QLineEdit()
        self.tracking_surface.setText(str(configuration.tracking_surface))

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


    def save_settings(self, evt=None):
        """
        Store the changes to the widgets to the config.yaml file
        This function should probably do some validation
        """
        config = configuration.config
        for key, nested in configuration.settings.items():
            for nested_key, old_value in nested.items():
                if hasattr(self, nested_key):
                    new_value = getattr(self, nested_key).text()
                    if type(old_value) == int:
                        new_value = int(new_value)
                    if type(old_value) == float:
                        new_value = float(new_value)
                    if old_value != new_value:
                        config[key][nested_key] = new_value
                        # TODO This call doesn't really seem to work
                        setattr(configuration, nested_key, new_value)

        for key, old_value in configuration.shortcut_strings.items():
            if hasattr(self, key):
                new_value = getattr(self, key).text()
                config["shortcuts"][key] = str(new_value)
                key_sequence = QtGui.QKeySequence.fromString(new_value)
                setattr(configuration, key, key_sequence)

        # TODO A problem is that changing configuration doesn't assign the attributes in configuration itself.
        # Guess I should modify config and have everything read from that?
        # I've added setattr calls for now to try and get it working anyway

        configuration.save_settings(config)
        # Notify the rest of the application that the configuration have changed
        # TODO: changes here should propagate to the rest of the application (like the database screen)
        pub.sendMessage("changed_settings")

    def change_measurement_folder(self, evt=None):
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your measurements",
                                             configuration.measurement_folder)

        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        #self.file_dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # Store the default in case we don't make a change
        folder = self.measurement_folder.text()
        # Change where configuration.measurement_folder is pointing too
        if self.file_dialog.exec_():
            folder = self.file_dialog.selectedFiles()[0]

        # Then change that, so we always keep our 'default' measurements_folder
        configuration.measurement_folder = folder
        self.measurement_folder.setText(folder)

    def change_database_folder(self, evt=None):
        # Open a file dialog
        self.file_dialog = QtGui.QFileDialog(self,
                                             "Select the folder containing your database",
                                             configuration.database_folder)

        self.file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        self.file_dialog.setViewMode(QtGui.QFileDialog.Detail)

        # Store the default in case we don't make a change
        folder = self.database_folder.text()
        # Change where configuration.measurement_folder is pointing too
        if self.file_dialog.exec_():
            folder = self.file_dialog.selectedFiles()[0]

        # Then change that, so we always keep our 'default' measurements_folder
        configuration.database_folder = folder
        self.database_folder.setText(folder)


    def create_toolbar_actions(self):
        self.save_settings_action = gui.create_action(text="&Save Settings",
                                                        shortcut=QtGui.QKeySequence("CTRL+S"),
                                                        icon=QtGui.QIcon(
                                                            os.path.join(os.path.dirname(__file__),
                                                                         "../images/save_icon.png")),
                                                        tip="Save configuration",
                                                        checkable=True,
                                                        connection=self.save_settings
        )

        self.actions = [self.save_settings_action]

        for action in self.actions:
            self.toolbar.addAction(action)