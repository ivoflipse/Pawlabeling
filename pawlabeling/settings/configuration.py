#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os
import sys
from PySide.QtCore import *
from PySide.QtGui import *

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
    QColor(Qt.green),
    QColor(Qt.darkGreen),
    QColor(Qt.red),
    QColor(Qt.darkRed),
    QColor(Qt.gray),
    QColor(Qt.white),
    QColor(Qt.yellow)
]

# Keyboard_shortcuts
desktop = True
if desktop:
    left_front = QKeySequence(Qt.Key_7)
    left_hind = QKeySequence(Qt.Key_1)
    right_front = QKeySequence(Qt.Key_9)
    right_hind = QKeySequence(Qt.Key_3)
    previous_paw = QKeySequence(Qt.Key_4)
    next_paw = QKeySequence(Qt.Key_6)
    remove_label = QKeySequence(Qt.Key_5)
    invalid_paw = QKeySequence(Qt.Key_Delete)
else:
    left_front = QKeySequence(Qt.Key_U)
    left_hind = QKeySequence(Qt.Key_N)
    right_front = QKeySequence(Qt.Key_O)
    right_hind = QKeySequence(Qt.Key_Comma)
    previous_paw = QKeySequence(Qt.Key_J)
    next_paw = QKeySequence(Qt.Key_L)
    remove_label = QKeySequence(Qt.Key_K)
    invalid_paw = QKeySequence(Qt.Key_Delete)


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
main_window_left = 0
main_window_top = 25
main_window_width = 1400
main_window_height = 900
main_window_size = QRect(main_window_left, main_window_top, main_window_width, main_window_height)

# These are more size hints, since the other parts of the window set minimum sizes
# I might make those available here too
entire_plate_widget_width = 800
entire_plate_widget_height = 400

paws_widget_height = 200

# This determines the amount of interpolation used to increase the size of the canvas of entire plate and paw
# Decrease this value if you have a smaller screen
degree = 4

# Change the output to a logging file if you want to enable logging
# TODO what happens if this gets imported multiple times and I would change the logging to something different?
logging = True
print_location = sys.stdout
