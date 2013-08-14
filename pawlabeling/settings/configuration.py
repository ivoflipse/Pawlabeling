import os
import yaml
from PySide import QtGui, QtCore
import logging

app_name = "Paw Labeling tool"

settings_folder = os.path.dirname(__file__)
root_folder = os.path.dirname(settings_folder)

config_file = os.path.join(settings_folder, "config.yaml")
config_example_file = os.path.join(settings_folder, "config_example.yaml")

# Check if there's a config.yaml, else copy the example version and write it to config.yaml
if not os.path.exists(config_file):
    with open(config_example_file,"r") as input_file:
        output_string = ""
        for line in input_file:
            output_string += line

    with open(config_file, "w") as output_file:
        for line in output_string:
            output_file.write(line)

# To use settings other than my default ones, change config.yaml
with open(config_file,"r") as input_file:
    config = yaml.load(input_file)

# Check if the existing yaml file is complete
with open(config_example_file,"r") as input_file:
    config_example = yaml.load(input_file)

# Go through all the keys, even the nested ones (only one level!)
for key, value in config_example.items():
    if key not in config:
        config[key] = config_example[key]
    if type(value) == dict:
        for nested_key, nested_value in value.items():
            if nested_key not in config[key]:
                config[key][nested_key] = nested_value

# Write any changes back to the config.yaml file
with open(config_file, "w") as output_file:
    output_file.write(yaml.dump(config,  default_flow_style=False))

# Lookup table for converting indices to labels
paw_dict = {
    0: "LF",
    1: "LH",
    2: "RF",
    3: "RH",
    -3: "Invalid",
    -2: "NA",
    -1: "Current"
}
# Colors for displaying bounding boxes
colors = [
    QtGui.QColor(QtCore.Qt.green),
    QtGui.QColor(QtCore.Qt.darkGreen),
    QtGui.QColor(QtCore.Qt.red),
    QtGui.QColor(QtCore.Qt.darkRed),
    QtGui.QColor(QtCore.Qt.gray),
    QtGui.QColor(QtCore.Qt.white),
    QtGui.QColor(QtCore.Qt.yellow)
]

# Keyboard_shortcuts
desktop = True
if desktop:
    left_front = QtGui.QKeySequence(QtCore.Qt.Key_7)
    left_hind = QtGui.QKeySequence(QtCore.Qt.Key_1)
    right_front = QtGui.QKeySequence(QtCore.Qt.Key_9)
    right_hind = QtGui.QKeySequence(QtCore.Qt.Key_3)
    previous_paw = QtGui.QKeySequence(QtCore.Qt.Key_4)
    next_paw = QtGui.QKeySequence(QtCore.Qt.Key_6)
    remove_label = QtGui.QKeySequence(QtCore.Qt.Key_5)
    invalid_paw = QtGui.QKeySequence(QtCore.Qt.Key_Delete)
else:
    left_front = QtGui.QKeySequence(QtCore.Qt.Key_U)
    left_hind = QtGui.QKeySequence(QtCore.Qt.Key_N)
    right_front = QtGui.QKeySequence(QtCore.Qt.Key_O)
    right_hind = QtGui.QKeySequence(QtCore.Qt.Key_Comma)
    previous_paw = QtGui.QKeySequence(QtCore.Qt.Key_J)
    next_paw = QtGui.QKeySequence(QtCore.Qt.Key_L)
    remove_label = QtGui.QKeySequence(QtCore.Qt.Key_K)
    invalid_paw = QtGui.QKeySequence(QtCore.Qt.Key_Delete)

measurement_folder = config["folders"]["measurement_folder"]
store_results_folder = config["folders"]["store_results_folder"]

# If the path isn't the one created by me
if store_results_folder[0] == ".":
    # Convert them to absolute paths
    measurement_folder = os.path.join(root_folder, "samples\\Measurements")
    store_results_folder = os.path.join(root_folder, "samples\\Labels")
else:
    try:
        # Add the folder for the store_results_folder data if it doesn't exist
        if not os.path.exists(store_results_folder):
            os.mkdir(store_results_folder)
    except Exception, e:
        print("Couldn't create store results folder")
        print("Exception: {}".format(e))

brand = "rsscan"
frequency = 124

if brand == "rsscan":
    sensor_width = 0.508
    sensor_height = 0.762
else:
    sensor_width = config["sensors"]["width"]
    sensor_height = config["sensors"]["height"]
sensor_surface = sensor_width * sensor_height

# Thresholds for utility.incomplete_step
start_force_percentage = config["thresholds"]["start_force_percentage"]
end_force_percentage = config["thresholds"]["end_force_percentage"]
# Thresholds for tracking
tracking_temporal = config["thresholds"]["tracking_temporal"]
tracking_spatial = config["thresholds"]["tracking_spatial"]
tracking_surface = config["thresholds"]["tracking_surface"]
padding_factor = config["thresholds"]["padding_factor"]

main_window_left = config["widgets"]["main_window_left"]
main_window_top = config["widgets"]["main_window_top"]
main_window_width = config["widgets"]["main_window_width"]
main_window_height = config["widgets"]["main_window_height"]
main_window_size = QtCore.QRect(main_window_left, main_window_top, main_window_width, main_window_height)

entire_plate_widget_width = config["widgets"]["entire_plate_widget_width"]
entire_plate_widget_height = config["widgets"]["entire_plate_widget_height"]
paws_widget_height = config["widgets"]["paws_widget_height"]

# This determines the amount of interpolation used to increase the size of the canvas of entire plate and paw
# Decrease this value if you have a smaller screen
interpolation_entire_plate = config["interpolation_degree"]["entire_plate"]
interpolation_paws_widget = config["interpolation_degree"]["paws_widget"]
interpolation_results = config["interpolation_degree"]["results"]

logging_levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}
# Choose from: debug, info, warning, error, critical
level = "debug"
logging_level = logging_levels.get(level, "debug")

def setup_logging():
    # create logger with the application
    logger = logging.getLogger("logger")

    # Add the lower check just in case
    logger.setLevel(logging_level)
    # create file handler which logs even debug messages
    log_folder = os.path.join(root_folder, "log")
    log_file_path = os.path.join(log_folder, "pawlabeling_log.log")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging_level)

    # create console handler with a higher log level
    console_handler = logging.StreamHandler()
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
