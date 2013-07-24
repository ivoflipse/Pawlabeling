import os
import sys
from PySide import QtGui, QtCore

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


# The first measurement_folder is the folder which stores all the measurement files
measurement_folder = ".\\samples\\Measurements"
store_results_folder = ".\\samples\\Labels"
# Add the folder for the store_results_folder data if it doesn't exist
if not os.path.exists(store_results_folder):
    os.mkdir(store_results_folder)

brand = "rsscan"
# TODO use this if you start displaying results and want to display actual milliseconds
frequency = 124

if brand == "rsscan":
    sensor_width = 0.5
    sensor_height = 0.7
else:
    sensor_width = 1
    sensor_height = 1
sensor_surface = sensor_width * sensor_height

# These values dictate how large the app will be, best not touch window_top
# since you'll lose the buttons to min/maximize the window
if desktop:
    main_window_left = 0
    main_window_top = 25
    main_window_width = 1400
    main_window_height = 900
    main_window_size = QtCore.QRect(main_window_left, main_window_top, main_window_width, main_window_height)
    # These are more size hints, since the other parts of the window set minimum sizes
    # I might make those available here too
    entire_plate_widget_width = 800
    entire_plate_widget_height = 400
    paws_widget_height = 200
else:
    main_window_left = 0
    main_window_top = 25
    main_window_width = 1440
    main_window_height = 830
    main_window_size = QtCore.QRect(main_window_left, main_window_top, main_window_width, main_window_height)
    entire_plate_widget_width = 800
    entire_plate_widget_height = 450
    paws_widget_height = 170

# This determines the amount of interpolation used to increase the size of the canvas of entire plate and paw
# Decrease this value if you have a smaller screen
degree = 4

# Change the output to a logging file if you want to enable logging
# TODO what happens if this gets imported multiple times and I would change the logging to something different?
logging = True
print_location = sys.stdout
