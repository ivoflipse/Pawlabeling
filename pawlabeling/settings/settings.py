import os
import shutil
import sys
import yaml
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
        self.logger = self.setup_logging()

        # Lookup table for all the different settings
        self.lookup_table = {"folders": {"measurement_folder": "",
                                         "database_file":"",
                                         "database_folder":""},
                             # "brands": [{"brand": "",
                             #           "model": "",
                             #           "frequency": "",
                             #           "sensor_width":"",
                             #           "sensor_height":"",
                             #           "sensor_surface":""}],
                             "interpolation_degree": {"interpolation_entire_plate": "",
                                                      "interpolation_contact_widgets": "",
                                                      "interpolation_results": ""},
                             "thresholds": {"start_force_percentage": "",
                                            "end_force_percentage": "",
                                            "tracking_temporal": "",
                                            "tracking_spatial": "",
                                            "tracking_surface": ""},
                             "application": {"zip_files": "",
                                             "show_maximized": ""},
        }

    def restore_last_session(self):
        key = "restore_last_session"
        default_value = True
        setting_value = self.value(key)
        if isinstance(setting_value, bool):
            return setting_value
        else:
            return default_value

    def keyboard_shortcuts(self):
        key = "keyboard_shortcuts"
        default_value = {
            "left_front": "7",
            "left_hind": "3",
            "right_front": "9",
            "right_hind": "1",
            "previous_contact": "4",
            "next_contact": "6",
            "remove_label": "5",
            "invalid_contact": "Delete"
        }
        setting_value = self.value(key)
        if isinstance(setting_value, list):
            return self.convert_shortcuts(setting_value)
        else:
            return self.convert_shortcuts(default_value)

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

    def folders(self):
        key = "folders"
        default_value = {
            "measurement_folder": os.path.join(self.root_folder, "samples\\Measurements"),
            "database_folder": ".\\database",
            "database_file": os.path.join(self.root_folder, "database\\data.h5")
        }
        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            return setting_value
        else:
            return default_value

    # TODO It would be nice if this had a key that mapped to each plate
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

    def thresholds(self):
        key = "thresholds"
        default_value = {
            "start_force_percentage": 0.25,
            "end_force_percentage": 0.25,
            "tracking_temporal": 0.5,
            "tracking_spatial": 1.25,
            "tracking_surface": 0.25,
            "padding_factor": 1
        }
        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            return setting_value
        else:
            return default_value

    def widgets(self):
        key = "widgets"
        default_value = {
            "main_window_left": 0,
            "main_window_top": 25,
            "main_window_width": 1440,
            "main_window_height": 830,
            "main_window_size": QtCore.QRect(0, 25, 1440, 830), # How will I make this user definable?
            "entire_plate_widget_width": 800,
            "entire_plate_widget_height": 450,
            "contacts_widget_height": 170,
        }
        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            return setting_value
        else:
            return default_value

    def interpolation(self):
        """
        This determines the amount of interpolation used to increase the size of the
        canvas of entire plate and contact. Decrease this value if you have a smaller screen
        """
        key = "interpolation"
        default_value = {
            "interpolation_entire_plate": 4,
            "interpolation_contact_widgets": 8,
            "interpolation_results": 16
        }
        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            return setting_value
        else:
            return default_value

    def application(self):
        key = "application"
        default_value = {
            "zip_files": True,
            "show_maximized": True,
            "application_font": QtGui.QFont("Helvetica", 10),
            "label_font": QtGui.QFont("Helvetica", 14, QtGui.QFont.Bold),
            "date_format": QtCore.QLocale.system().dateFormat(QtCore.QLocale.ShortFormat)
        }
        setting_value = self.value(key)
        if isinstance(setting_value, dict):
            return setting_value
        else:
            return default_value

    def read_settings(self):
        settings = {}
        settings["contact_dict"] = self.contact_dict()
        settings["colors"] = self.colors()
        settings["restore_last_session"] = self.restore_last_session()
        settings["keyboard_shortcuts"] = self.keyboard_shortcuts()
        settings["folders"] = self.folders()
        settings["brands"] = self.brands()
        settings["thresholds"] = self.thresholds()
        settings["widgets"] = self.widgets()
        settings["interpolation"] = self.interpolation()
        settings["application"] = self.application()
        return settings

    def load_settings(self, settings):
        self.user_settings(settings)
        # Here it seems I need to add a bunch more attributes too

    def save_settings(self, settings):
        """
        """
        for key, value in settings.items():
            self.write_value(key, value)

    def user_settings(self, settings):
        key = 'restore_last_session'
        if key in settings:
            self.restore_last_session = settings[key]

            # I'll have to add user loadable things here later

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



