import os
import sys
from collections import defaultdict
from PySide import QtGui, QtCore
from pubsub import pub
import logging

__version__ = '0.1'


class Settings(QtCore.QSettings):
    def __init__(self):
        self.settings_folder = os.path.dirname(__file__)
        self.root_folder = os.path.dirname(self.settings_folder)
        # Get the file paths for the two config files
        # self.settings_file = os.path.join(self.settings_folder, "config.yaml")
        self.settings_file = os.path.join(self.settings_folder, "settings.ini")

        QtCore.QCoreApplication.setOrganizationName("Flipse R&D")
        QtCore.QCoreApplication.setOrganizationDomain("flipserd.com")
        QtCore.QCoreApplication.setApplicationName("Paw Labeling")
        QtCore.QCoreApplication.setApplicationVersion(getVersion())

        super(Settings, self).__init__(self.settings_file, QtCore.QSettings.IniFormat)
        # System-wide settings will not be searched as a fallback
        self.setFallbacksEnabled(False)
        # Load everything we need
        self.read_settings()

        # Lookup table for all the different settings
        self.lookup_table = {
            "plate": ["plate"],
            "folders": ["measurement_folder", "database_file", "database_folder"],
            "keyboard_shortcuts": ["left_front", "left_hind", "right_front", "right_hind",
                                   "previous_contact", "next_contact", "invalid_valid", "remove_label"],
            "interpolation_degree": ["interpolation_entire_plate",
                                     "interpolation_contact_widgets",
                                     "interpolation_results"],
            "thresholds": ["start_force_percentage",
                           "end_force_percentage",
                           "tracking_temporal",
                           "tracking_spatial",
                           "tracking_surface"],
            "application": ["zip_files", "show_maximized", "restore_last_session"],
        }

        self.create_contact_dict()
        self.create_colors()

        # Set up the logger
        self.setup_logging()

    def create_contact_dict(self):
        # Lookup table for converting indices to labels
        self.contact_dict = {
            0: "LF",
            1: "LH",
            2: "RF",
            3: "RH",
            -3: "Invalid",
            -2: "NA",
            -1: "Current"
        }

    def create_colors(self):
        # Colors for displaying bounding boxes
        self.colors = [
            QtGui.QColor(QtCore.Qt.green),
            QtGui.QColor(QtCore.Qt.darkGreen),
            QtGui.QColor(QtCore.Qt.red),
            QtGui.QColor(QtCore.Qt.darkRed),
            QtGui.QColor(QtCore.Qt.gray),
            QtGui.QColor(QtCore.Qt.white),
            QtGui.QColor(QtCore.Qt.yellow)
        ]

    def plate(self):
        key = "plate/plate"
        default_value = ""
        setting_value = self.value(key)
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def left_front(self):
        key = "keyboard_shortcuts/left_front"
        default_value = QtGui.QKeySequence.fromString("7")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def left_hind(self):
        key = "keyboard_shortcuts/left_hind"
        default_value = QtGui.QKeySequence.fromString("1")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def right_front(self):
        key = "keyboard_shortcuts/right_front"
        default_value = QtGui.QKeySequence.fromString("9")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def right_hind(self):
        key = "keyboard_shortcuts/right_hind"
        default_value = QtGui.QKeySequence.fromString("3")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def previous_contact(self):
        key = "keyboard_shortcuts/previous_contact"
        default_value = QtGui.QKeySequence.fromString("4")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def next_contact(self):
        key = "keyboard_shortcuts/next_contact"
        default_value = QtGui.QKeySequence.fromString("6")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def invalid_contact(self):
        key = "keyboard_shortcuts/invalid_contact"
        default_value = QtGui.QKeySequence.fromString("Delete")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def remove_label(self):
        key = "keyboard_shortcuts/remove_label"
        default_value = QtGui.QKeySequence.fromString("5")
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QKeySequence):
            return setting_value
        else:
            return default_value

    def measurement_folder(self):
        key = "folders/measurement_folder"
        default_value = os.path.join(self.root_folder, "samples\\Measurements")
        setting_value = self.value(key)
        # Check if this folder even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def database_folder(self):
        key = "folders/database_folder"
        default_value = os.path.join(self.root_folder, "database")
        setting_value = self.value(key)
        # Check if this folder even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def database_file(self):
        key = "folders/database_file"
        default_value = os.path.join(self.root_folder, "database\\data.h5")
        setting_value = self.value(key)
        # Check if this folder even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        # TODO what if the default value doesn't exist either
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def start_force_percentage(self):
        key = "thresholds/start_force_percentage"
        default_value = 0.25
        setting_value = self.value(key)
        if isinstance(setting_value, float):
            return setting_value
        else:
            return default_value

    def end_force_percentage(self):
        key = "thresholds/end_force_percentage"
        default_value = 0.25
        setting_value = self.value(key)
        if isinstance(setting_value, float):
            return setting_value
        else:
            return default_value

    def tracking_temporal(self):
        key = "thresholds/tracking_temporal"
        default_value = 0.5
        setting_value = self.value(key)
        if isinstance(setting_value, float):
            return setting_value
        else:
            return default_value

    def tracking_spatial(self):
        key = "thresholds/tracking_spatial"
        default_value = 1.25
        setting_value = self.value(key)
        if isinstance(setting_value, float):
            return setting_value
        else:
            return default_value

    def tracking_surface(self):
        key = "thresholds/tracking_surface"
        default_value = 0.25
        setting_value = self.value(key)
        if isinstance(setting_value, float):
            return setting_value
        else:
            return default_value

    def padding_factor(self):
        key = "thresholds/padding_factor"
        default_value = 1
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def main_window_left(self):
        key = "thresholds/padding_factor"
        default_value = 0
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def main_window_top(self):
        key = "thresholds/main_window_top"
        default_value = 25
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def main_window_width(self):
        key = "thresholds/main_window_width"
        default_value = 1440
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def main_window_height(self):
        key = "thresholds/main_window_height"
        default_value = 830
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def main_window_size(self):
        key = "thresholds/main_window_size"
        default_value = QtCore.QRect(0, 25, 1440, 830)
        setting_value = self.value(key)
        if isinstance(setting_value, QtCore.QRect):
            return setting_value
        else:
            return default_value

    def entire_plate_widget_width(self):
        key = "thresholds/entire_plate_widget_width"
        default_value = 800
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def entire_plate_widget_height(self):
        key = "thresholds/entire_plate_widget_height"
        default_value = 450
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def contacts_widget_height(self):
        key = "thresholds/contacts_widget_height"
        default_value = 170
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def interpolation_entire_plate(self):
        key = "interpolation/interpolation_entire_plate"
        default_value = 4
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def interpolation_contact_widgets(self):
        key = "interpolation/interpolation_contact_widgets"
        default_value = 8
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def interpolation_results(self):
        key = "interpolation/interpolation_results"
        default_value = 16
        setting_value = self.value(key)
        if isinstance(setting_value, int):
            return setting_value
        else:
            return default_value

    def zip_files(self):
        key = "interpolation/zip_files"
        default_value = True
        setting_value = self.value(key)
        if isinstance(setting_value, bool):
            return setting_value
        else:
            return default_value

    def show_maximized(self):
        key = "application/show_maximized"
        default_value = False
        setting_value = self.value(key)
        if isinstance(setting_value, bool):
            return setting_value
        else:
            return default_value

    def application_font(self):
        key = "application/application_font"
        default_value = QtGui.QFont("Helvetica", 10)
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QFont):
            return setting_value
        else:
            return default_value

    def label_font(self):
        key = "application/label_font"
        default_value = QtGui.QFont("Helvetica", 14, QtGui.QFont.Bold)
        setting_value = self.value(key)
        if isinstance(setting_value, QtGui.QFont):
            return setting_value
        else:
            return default_value

    def date_format(self):
        key = "application/date_format"
        default_value = QtCore.QLocale.system().dateFormat(QtCore.QLocale.ShortFormat)
        setting_value = self.value(key)
        if isinstance(setting_value, QtCore.QLocale.FormatType):
            return setting_value
        else:
            return default_value

    def restore_last_session(self):
        key = "application/restore_last_session"
        default_value = True
        setting_value = self.value(key)
        if isinstance(setting_value, bool):
            return setting_value
        else:
            return default_value

    def read_settings(self):
        self.settings = defaultdict()
        self.settings["plate/plate"] = self.plate()

        self.settings["keyboard_shortcuts/left_front"] = self.left_front()
        self.settings["keyboard_shortcuts/left_hind"] = self.left_hind()
        self.settings["keyboard_shortcuts/right_front"] = self.right_front()
        self.settings["keyboard_shortcuts/right_hind"] = self.right_hind()
        self.settings["keyboard_shortcuts/previous_contact"] = self.previous_contact()
        self.settings["keyboard_shortcuts/next_contact"] = self.next_contact()
        self.settings["keyboard_shortcuts/remove_label"] = self.remove_label()
        self.settings["keyboard_shortcuts/invalid_contact"] = self.invalid_contact()

        self.settings["folders/measurement_folder"] = self.measurement_folder()
        self.settings["folders/database_folder"] = self.database_folder()
        self.settings["folders/database_file"] = self.database_file()

        self.settings["thresholds/start_force_percentage"] = self.start_force_percentage()
        self.settings["thresholds/end_force_percentage"] = self.end_force_percentage()
        self.settings["thresholds/tracking_temporal"] = self.tracking_temporal()
        self.settings["thresholds/tracking_spatial"] = self.tracking_spatial()
        self.settings["thresholds/tracking_surface"] = self.tracking_surface()
        self.settings["thresholds/padding_factor"] = self.padding_factor()

        self.settings["widgets/main_window_left"] = self.main_window_left()
        self.settings["widgets/main_window_top"] = self.main_window_top()
        self.settings["widgets/main_window_width"] = self.main_window_width()
        self.settings["widgets/main_window_height"] = self.main_window_height()
        self.settings["widgets/main_window_size"] = self.main_window_size()
        self.settings["widgets/entire_plate_widget_width"] = self.entire_plate_widget_width()
        self.settings["widgets/entire_plate_widget_height"] = self.entire_plate_widget_height()
        self.settings["widgets/contacts_widget_height"] = self.contacts_widget_height()

        self.settings["interpolation/interpolation_entire_plate"] = self.interpolation_entire_plate()
        self.settings["interpolation/interpolation_contact_widgets"] = self.interpolation_contact_widgets()
        self.settings["interpolation/interpolation_results"] = self.interpolation_results()

        self.settings["application/zip_files"] = self.zip_files()
        self.settings["application/show_maximized"] = self.show_maximized()
        self.settings["application/application_font"] = self.application_font()
        self.settings["application/label_font"] = self.label_font()
        self.settings["application/date_format"] = self.date_format()
        self.settings["application/restore_last_session"] = self.restore_last_session()

        return self.settings

    def save_settings(self, settings):
        """
        """
        for key, value in settings.iteritems():
            print key, value
            self.write_value(key, value)

    def write_value(self, key, value):
        """
        Write an entry to the configuration file.
        :Parameters:
        - `key`: the name of the property we want to set.
        - `value`: the value we want to assign to the property
        """
        try:
            self.setValue(key, value)
            if self.status():
                raise Exception(u'{0}={1}'.format(key, value))
            self.sync()
        except Exception, e:
            print(e)

    def setup_logging(self):
        logging_levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        # These should probably be user definable

        # Choose from: debug, info, warning, error, critical
        debug_level = "debug"
        logging_level = logging_levels.get(debug_level, "debug")

        # create logger with the application
        self.logger = logging.getLogger("logger")

        # Add the lower check just in case
        self.logger.setLevel(logging_level)
        # create file handler which logs even debug messages
        log_folder = os.path.join(self.root_folder, "log")
        log_file_path = os.path.join(log_folder, "pawlabeling_log.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging_level)

        # create console handler with a higher log debug_level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)

        # create formatter and add it to the handlers
        file_formatter = logging.Formatter('%(asctime)s - %(name)% - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s - %(filename)s - Line: %(lineno)d - %(message)s')
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        # add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("-----------------------------------")
        self.logger.info("Log system successfully initialised")
        self.logger.info("-----------------------------------")

    def setup_plates(self):
        plates = [
            {"brand": "rsscan",
             "model": "0.5m 2nd gen",
             "number_of_rows": 64,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "rsscan",
             "model": "1m 2nd gen",
             "number_of_rows": 128,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "rsscan",
             "model": "2m 2nd gen",
             "number_of_rows": 256,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "rsscan",
             "model": "0.5m USB",
             "number_of_rows": 64,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "rsscan",
             "model": "1m USB",
             "number_of_rows": 128,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "rsscan",
             "model": "1.5m USB",
             "number_of_rows": 192,
             "number_of_columns": 63,
             "sensor_width": 0.508,
             "sensor_height": 0.762,
             "sensor_surface": 0.387096
            },
            {"brand": "zebris",
             "model": "FDM 1m",
             "number_of_rows": 176,
             "number_of_columns": 64,
             "sensor_width": 0.846,
             "sensor_height": 0.846,
             "sensor_surface": 0.715716
            },
            {"brand": "zebris",
             "model": "FDM 1.5m",
             "number_of_rows": 240,
             "number_of_columns": 64,
             "sensor_width": 0.846,
             "sensor_height": 0.846,
             "sensor_surface": 0.715716
            },
            {"brand": "zebris",
             "model": "FDM 2m",
             "number_of_rows": 352,
             "number_of_columns": 64,
             "sensor_width": 0.846,
             "sensor_height": 0.846,
             "sensor_surface": 0.715716
            },
            {"brand": "novel",
             "model": "emed",
             "number_of_rows": 256,
             "number_of_columns": 256,
             "sensor_width": 0.5,
             "sensor_height": 0.5,
             "sensor_surface": 0.25
            },
            {"brand": "novel",
             "model": "emed-a50",
             "number_of_rows": 55,
             "number_of_columns": 32,
             "sensor_width": 0.7,
             "sensor_height": 0.7,
             "sensor_surface": 0.49
            },
            {"brand": "novel",
             "model": "emed-c50",
             "number_of_rows": 79,
             "number_of_columns": 48,
             "sensor_width": 0.5,
             "sensor_height": 0.5,
             "sensor_surface": 0.25
            },
            {"brand": "novel",
             "model": "emed-n50",
             "number_of_rows": 95,
             "number_of_columns": 64,
             "sensor_width": 0.5,
             "sensor_height": 0.5,
             "sensor_surface": 0.25
            },
            {"brand": "novel",
             "model": "emed-q100",
             "number_of_rows": 95,
             "number_of_columns": 64,
             "sensor_width": 0.5,
             "sensor_height": 0.5,
             "sensor_surface": 0.25
            },
            {"brand": "novel",
             "model": "emed-x400",
             "number_of_rows": 95,
             "number_of_columns": 64,
             "sensor_width": 0.5,
             "sensor_height": 0.5,
             "sensor_surface": 0.25
            }
        ]
        return plates


class MissingIdentifier(Exception):
    pass


def getVersion():
    """The application version."""
    return __version__


settings = Settings()