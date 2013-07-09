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

# The first measurement_folder is the folder which stores all the measurement files
measurement_folder = "C:\\Exports\\"
store_results_folder = "C:\\LabelsStored\\"
# Add the folder for the store_results_folder data if it doesn't exist
if not os.path.exists(store_results_folder):
    os.mkdir(store_results_folder)

# TODO tie in this information to use a different loading function
brand = "rsscan"
# TODO use this if you start displaying results and want to display actual milliseconds
frequency = 124

# These values dictate how large the app will be, best not touch window_top
# since you'll lose the buttons to min/maximize the window
main_window_left = 0
main_window_top = 25
main_window_width = 2250
main_window_height = 1250
main_window_size = QRect(main_window_left, main_window_top, main_window_width, main_window_height)

# These are more size hints, since the other parts of the window set minimum sizes
# I might make those available here too
entire_plate_widget_width = 800
entire_plate_widget_height = 800

# This determines the amount of interpolation used to increase the size of the canvas of entire plate and paw
# Decrease this value if you have a smaller screen
degree = 6

# Change the output to a logging file if you want to enable logging
# TODO what happens if this gets imported multiple times and I would change the logging to something different?
logging = True
print_location = sys.stdout
