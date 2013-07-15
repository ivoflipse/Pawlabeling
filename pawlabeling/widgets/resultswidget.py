#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PySide.QtCore import *
from PySide.QtGui import *

from widgets.results import twodimviewwidget, pressureviewwidget, forceviewwidget


class ResultsWidget(QWidget):
    def __init__(self, parent):
        super(ResultsWidget, self).__init__(parent)

        self.two_dim_view_widget = twodimviewwidget.TwoDimViewWidget(self, degree=4)
        self.pressure_view_widget = pressureviewwidget.PressureViewWidget(self)
        self.force_view_widget = forceviewwidget.ForceViewWidget(self)

        self.widgets = [self.two_dim_view_widget,
                        self.pressure_view_widget,
                        self.force_view_widget]

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.two_dim_view_widget, "2D view")
        self.tab_widget.addTab(self.pressure_view_widget, "Pressure")
        self.tab_widget.addTab(self.force_view_widget, "Force")

        self.tab_widget.currentChanged.connect(self.update_active_widget)

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def update_widgets(self, paw_labels, paw_data, average_data):
        self.paw_labels = paw_labels
        self.paw_data = paw_data
        self.average_data = average_data

        self.update_active_widget()

    def update_active_widget(self):
        current_tab = self.tab_widget.currentIndex()
        widget = self.widgets[current_tab]
        widget.update_paws(self.paw_labels, self.paw_data, self.average_data)

    def update_n_max(self, n_max):
        for widget in self.widgets:
            widget.update_n_max(n_max)

    def change_frame(self, frame):
        self.frame = frame
        for widget in self.widgets:
            widget.change_frame(frame)