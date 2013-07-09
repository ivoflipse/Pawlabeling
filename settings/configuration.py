#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os
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

path = "C:\\Exports\\"
store_path = "C:\\LabelsStored\\"

# Add the folder for the store_path data if it doesn't exist
if not os.path.exists(store_path):
    os.mkdir(store_path)

brand = "rsscan"
frequency = 124

logging = True

main_window_left = 0
main_window_top = 25
main_window_width = 2250
main_window_height = 1250
main_window_size = QRect(main_window_left, main_window_top, main_window_width, main_window_height)

entire_plate_widget_width = 800
entire_plate_widget_height = 800

degree = 6

def main():
    """
    I was trying to use a config file, but I haven't figured out how to share the info
    """
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read("configuration.ini")