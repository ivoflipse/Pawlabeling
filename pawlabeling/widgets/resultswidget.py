#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from collections import defaultdict

import numpy as np
from PySide.QtCore import *
from PySide.QtGui import *

from settings import configuration
from functions import utility, gui
from widgets.results import twodimviewwidget


class ResultsWidget(QWidget):
    def __init__(self, parent):
        super(ResultsWidget, self).__init__(parent)

        self.two_dim_view_widget = twodimviewwidget.TwoDimViewWidget(self, degree=4)
        self.pressure_widget = PressureWidget(self)
        self.force_widget = ForceWidget(self)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.two_dim_view_widget, "2D view")
        self.tab_widget.addTab(self.pressure_widget, "Pressure")
        self.tab_widget.addTab(self.force_widget, "Force")

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def update_widgets(self, paw_labels, paw_data, average_data):
        self.two_dim_view_widget.update_paws(paw_labels, paw_data, average_data)

    def update_n_max(self, n_max):
        self.two_dim_view_widget.update_n_max(n_max)

class PressureWidget(QWidget):
    def __init__(self, parent):
        super(PressureWidget, self).__init__(parent)
        self.label = QLabel("Pressure")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)

class ForceWidget(QWidget):
    def __init__(self, parent):
        super(ForceWidget, self).__init__(parent)
        self.label = QLabel("Force")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
