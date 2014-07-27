import os
import sys
from collections import defaultdict
from PySide import QtGui, QtCore
from pubsub import pub
import pkg_resources
pkg_resources.require("tables==3.1.1")
import tables
from tables.exceptions import ClosedNodeError
import logging

__version__ = '0.2'
# Using a global for now
__human__ = False


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
        #self.setFallbacksEnabled(False)

        # Lookup table for all the different settings
        self.lookup_table = {
            "plate": ["plate", "frequency"],
            "folders": ["measurement_folder", "database_file", "database_folder", "logging_folder"],
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

        # Create a database connection with PyTables
        database_file = self.database_file()
        self.table = tables.open_file(database_file, mode="a", title="Data")

        # Possibly I could provide a getter/setter such that you could change this on the fly
        self.create_contact_dict()
        self.create_colors()

        # Set up the logger
        self.setup_logging()

    def create_contact_dict(self):
        # Lookup table for converting indices to labels
        if __human__:
            self.contact_dict = {
                0: "Left",
                1: "Right",
                -2: "NA",
                -1: "Current"
            }
        else:
            self.contact_dict = {
                0: "LF",
                1: "LH",
                2: "RF",
                3: "RH",
                -2: "NA",
                -1: "Current"
            }

    def create_colors(self):
        # Colors for displaying bounding boxes
        if __human__:
            self.colors = [
                QtGui.QColor(QtCore.Qt.green),
                QtGui.QColor(QtCore.Qt.red),
                QtGui.QColor(QtCore.Qt.gray),
                QtGui.QColor(QtCore.Qt.white),
                QtGui.QColor(QtCore.Qt.yellow)
            ]

            self.matplotlib_color = [
                "#00FF00",
                "#FF0000",
                "w"
            ]
        else:
            self.colors = [
                QtGui.QColor(QtCore.Qt.green),
                QtGui.QColor(QtCore.Qt.darkGreen),
                QtGui.QColor(QtCore.Qt.red),
                QtGui.QColor(QtCore.Qt.darkRed),
                QtGui.QColor(QtCore.Qt.gray),
                QtGui.QColor(QtCore.Qt.white),
                QtGui.QColor(QtCore.Qt.yellow)
            ]

            self.matplotlib_color = [
                "#00FF00",
                "#008000",
                "#FF0000",
                "#800000",
                "w"
            ]

    def plate(self):
        key = "plate/plate"
        default_value = ""
        setting_value = self.value(key)
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def frequency(self):
        key = "plate/frequency"
        return self.value(key, "100")

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
        default_value = QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Delete)
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
        setting_value = str(self.value(key))
        # Check if this folder even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        return setting_value

    def database_folder(self):
        key = "folders/database_folder"
        default_value = os.path.join(self.root_folder, "database")
        setting_value = str(self.value(key))
        # Check if this folder even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        return setting_value

    def database_file(self):
        key = "folders/database_file"
        database_folder = self.database_folder()
        default_value = os.path.join(database_folder, "data.h5")
        setting_value = str(self.value(key))
        # Check if this file even exists, else return the relative path
        if not os.path.isfile(setting_value):
            return default_value
        return setting_value

    def logging_folder(self):
        key = "folders/logging_folder"
        default_value = os.path.join(self.root_folder, "log")
        setting_value = str(self.value(key))
        # Check if this file even exists, else return the relative path
        if not os.path.exists(setting_value):
            return default_value
        return setting_value

    def start_force_percentage(self):
        key = "thresholds/start_force_percentage"
        return float(self.value(key, 0.25))

    def end_force_percentage(self):
        key = "thresholds/end_force_percentage"
        return float(self.value(key, 0.25))

    def tracking_temporal(self):
        key = "thresholds/tracking_temporal"
        return float(self.value(key, 0.25))

    def tracking_spatial(self):
        key = "thresholds/tracking_spatial"
        return float(self.value(key, 1.25))

    def tracking_surface(self):
        key = "thresholds/tracking_surface"
        return float(self.value(key, 0.25))

    def padding_factor(self):
        key = "thresholds/padding_factor"
        return int(self.value(key, 1))

    def main_window_left(self):
        key = "widgets/main_window_left"
        default_value = 0
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def main_window_top(self):
        key = "widgets/main_window_top"
        default_value = 25
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def main_window_width(self):
        key = "widgets/main_window_width"
        default_value = 1440
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def main_window_height(self):
        key = "widgets/main_window_height"
        default_value = 830
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def main_window_size(self):
        key = "widgets/main_window_size"
        default_value = QtCore.QRect(0, 25, 1440, 830)
        setting_value = self.value(key)
        if isinstance(setting_value, QtCore.QRect):
            return setting_value
        else:
            return default_value

    def entire_plate_widget_width(self):
        key = "widgets/entire_plate_widget_width"
        default_value = 800
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def entire_plate_widget_height(self):
        key = "widgets/entire_plate_widget_height"
        default_value = 450
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def contacts_widget_height(self):
        key = "widgets/contacts_widget_height"
        default_value = 170
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def interpolation_entire_plate(self):
        key = "interpolation/interpolation_entire_plate"
        default_value = 4
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def interpolation_contact_widgets(self):
        key = "interpolation/interpolation_contact_widgets"
        default_value = 8
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
        else:
            return default_value

    def interpolation_results(self):
        key = "interpolation/interpolation_results"
        default_value = 16
        setting_value = self.value(key)
        if setting_value:
            return int(setting_value)
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
        """
        This function is used by the settings widget to get information about all the keys available
        and the type that their respective values have to be
        """
        self.settings = defaultdict()
        self.settings["plate/plate"] = self.plate()
        self.settings["plate/frequency"] = self.frequency()

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
        self.settings["folders/logging_folder"] = self.logging_folder()

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
            self.write_value(key, value)
        self.read_settings()

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
        log_folder = self.logging_folder()

        # If the folder doesn't exist, create it
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        log_file_path = os.path.join(log_folder, "pawlabeling_log.log")

        # If the file doesn't exist, create it (if possible)
        if not os.path.exists(log_file_path):
            try:
                open(log_file_path, "a+").close()
            except:
                # If it doesn't work, touche, no logging for you!
                pass

        # create formatter and add it to the handlers
        file_formatter = logging.Formatter('%(asctime)s - %(name)% - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s - %(filename)s - Line: %(lineno)d - %(message)s')

        # create console handler with a higher log debug_level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        if os.path.exists(log_file_path):
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(logging_level)
            file_handler.setFormatter(file_formatter)

            self.logger.addHandler(file_handler)

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