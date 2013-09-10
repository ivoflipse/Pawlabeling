import os
import sys
from collections import defaultdict
from PySide import QtGui, QtCore
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
        # product_name = '-'.join((application_name, version))

        super(Settings, self).__init__(self.settings_file, QtCore.QSettings.IniFormat)
        # System-wide settings will not be searched as a fallback
        self.setFallbacksEnabled(False)
        # Load everything we need
        self.load_settings(self.read_settings())

        # Lookup table for all the different settings
        self.lookup_table = {
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
            "application": ["zip_files",
                            "show_maximized"],
        }

    # TODO It would be nice if this had a key that mapped to each plate
    # TODO Possibly I should store these in PyTables instead of this hacked up solution
    def brands(self):
        key = "brands"
        default_value = [{"brand": "rsscan",
                          "model": "2m 2nd gen",
                          "frequency": 125,
                          "sensor_width": 0.508,
                          "sensor_height": 0.762,
                          "sensor_surface": 0.387096
                         },
                         {"brand": "zebris",
                          "model": "FDM 1m",
                          "frequency": 200,
                          "sensor_width": 0.846,
                          "sensor_height": 0.846,
                          "sensor_surface": 0.715716
                         },
                         {"brand": "novel",
                          "model": "emed",
                          "frequency": 100,
                          "sensor_width": 0.5,
                          "sensor_height": 0.5,
                          "sensor_surface": 0.25
                         }
        ]

        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            # This merges both dictionaries. Replace if the user can define this from the GUI
            return dict(default_value, **setting_value)
        else:
            return default_value


    def convert_shortcuts(self, shortcuts):
        new_shortcuts = {}
        for key, shortcut in shortcuts.items():
            new_shortcuts[key] = QtGui.QKeySequence.fromString(shortcut)
        return new_shortcuts

    def contact_dict(self):
        # Lookup table for converting indices to labels
        key = "contact_dict"
        default_value = {
            0: "LF",
            1: "LH",
            2: "RF",
            3: "RH",
            -3: "Invalid",
            -2: "NA",
            -1: "Current"
        }
        return default_value

    def colors(self):
        # Colors for displaying bounding boxes
        key = "colors"
        default_value = [
            QtGui.QColor(QtCore.Qt.green),
            QtGui.QColor(QtCore.Qt.darkGreen),
            QtGui.QColor(QtCore.Qt.red),
            QtGui.QColor(QtCore.Qt.darkRed),
            QtGui.QColor(QtCore.Qt.gray),
            QtGui.QColor(QtCore.Qt.white),
            QtGui.QColor(QtCore.Qt.yellow)
        ]
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
        if isinstance(setting_value, str) or isinstance(setting_value, unicode):
            return setting_value
        else:
            return default_value

    def database_folder(self):
        key = "folders/database_folder"
        default_value = ".\\database"
        setting_value = self.value(key)
        if isinstance(setting_value, str):
            return setting_value
        else:
            return default_value

    def database_file(self):
        key = "folders/database_file"
        default_value = os.path.join(self.root_folder, "database\\data.h5")
        setting_value = self.value(key)
        if isinstance(setting_value, str):
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
        key = "application/interpolation_results"
        default_value = True
        setting_value = self.value(key)
        if isinstance(setting_value, bool):
            return setting_value
        else:
            return default_value

    def show_maximized(self):
        key = "application/show_maximized"
        default_value = True
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
        settings = {}
        settings["contact_dict"] = self.contact_dict()
        settings["colors"] = self.colors()
        settings["brands"] = self.brands()

        settings["keyboard_shortcuts/left_front"] = self.left_front()
        settings["keyboard_shortcuts/left_hind"] = self.left_hind()
        settings["keyboard_shortcuts/right_front"] = self.right_front()
        settings["keyboard_shortcuts/right_hind"] = self.right_hind()
        settings["keyboard_shortcuts/previous_contact"] = self.previous_contact()
        settings["keyboard_shortcuts/next_contact"] = self.next_contact()
        settings["keyboard_shortcuts/remove_label"] = self.remove_label()
        settings["keyboard_shortcuts/invalid_contact"] = self.invalid_contact()

        settings["folders/measurement_folder"] = self.measurement_folder()
        settings["folders/database_folder"] = self.database_folder()
        settings["folders/database_file"] = self.database_file()

        settings["thresholds/start_force_percentage"] = self.start_force_percentage()
        settings["thresholds/end_force_percentage"] = self.end_force_percentage()
        settings["thresholds/tracking_temporal"] = self.tracking_temporal()
        settings["thresholds/tracking_spatial"] = self.tracking_spatial()
        settings["thresholds/tracking_surface"] = self.tracking_surface()
        settings["thresholds/padding_factor"] = self.padding_factor()

        settings["widgets/main_window_left"] = self.main_window_left()
        settings["widgets/main_window_top"] = self.main_window_top()
        settings["widgets/main_window_width"] = self.main_window_width()
        settings["widgets/main_window_height"] = self.main_window_height()
        settings["widgets/main_window_size"] = self.main_window_size()
        settings["widgets/entire_plate_widget_width"] = self.entire_plate_widget_width()
        settings["widgets/entire_plate_widget_height"] = self.entire_plate_widget_height()
        settings["widgets/contacts_widget_height"] = self.contacts_widget_height()

        settings["interpolation/interpolation_entire_plate"] = self.interpolation_entire_plate()
        settings["interpolation/interpolation_contact_widgets"] = self.interpolation_contact_widgets()
        settings["interpolation/interpolation_results"] = self.interpolation_results()

        settings["application/zip_files"] = self.zip_files()
        settings["application/show_maximized"] = self.show_maximized()
        settings["application/application_font"] = self.application_font()
        settings["application/label_font"] = self.label_font()
        settings["application/date_format"] = self.date_format()
        settings["application/restore_last_session"] = self.restore_last_session()

        return settings

    def load_settings(self, settings):
        self.user_settings(settings)
        # Here it seems I need to add a bunch more attributes too

    def save_settings(self, settings):
        """
        """
        for key, value in settings.items():
            self.write_value(key, value)
        self.sync()

    def user_settings(self, settings):
        pass
        # key = 'restore_last_session'
        # if key in settings:
        #     self.restore_last_session = settings[key]
        #
        #     # I'll have to add user loadable things here later

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
        logger = logging.getLogger("logger")

        # Add the lower check just in case
        logger.setLevel(logging_level)
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
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logger.info("-----------------------------------")
        logger.info("Log system successfully initialised")
        logger.info("-----------------------------------")

        return logger


class MissingIdentifier(Exception):
    pass


def getVersion():
    """The application version."""
    return __version__


settings = Settings()
