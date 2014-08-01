import logging
from collections import defaultdict
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pubsub import pub
from ...functions import utility, calculations
from ...settings import settings
from ...models import model



class OverviewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(OverviewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Asymmetry")
        self.parent = parent
        self.active = False

        self.left_front = OverviewView(self, "Left Front", 0)
        self.left_hind = OverviewView(self, "Left Hind", 1)
        self.right_front = OverviewView(self, "Right Front", 2)
        self.right_hind = OverviewView(self, "Right Hind", 3)


        self.overview_list = [self.left_front,
                               self.left_hind,
                               self.right_front,
                               self.right_hind]

        self.asymmetry_layout = QtGui.QGridLayout()
        self.asymmetry_layout.addWidget(self.left_front, 1, 0)
        self.asymmetry_layout.addWidget(self.left_hind, 1, 1)
        self.asymmetry_layout.addWidget(self.right_front, 2, 0)
        self.asymmetry_layout.addWidget(self.right_hind, 2, 1)


        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addLayout(self.asymmetry_layout)
        self.main_layout.addStretch(1)
        self.setLayout(self.main_layout)

        pub.subscribe(self.active_widget, "active_widget")

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            progress = 0
            pub.sendMessage("update_progress", progress=progress)
            for view in self.overview_list:
                view.draw()
            pub.sendMessage("update_progress", progress=100)


class OverviewView(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(OverviewView, self).__init__(parent)
        label_font = settings.settings.label_font()
        self.label = QtGui.QLabel(label)
        self.label.setFont(label_font)
        self.parent = parent
        self.model = model.model
        self.contact_label = contact_label

        self.frame = -1
        self.length = 0
        self.ratio = 1
        self.outlier_toggle = False
        self.average_toggle = False

        self.labels = {}
        self.text_boxes = {}

        self.columns = ["peak_force","peak_pressure","peak_surface","vertical_impulse",
                        "stance_duration","stance_percentage","step_duration","step_length"]

        self.result_layout = QtGui.QGridLayout()
        self.result_layout.setSpacing(10)

        self.result_layout.addWidget(self.label, 0, 0, columnSpan=1)

        for index, column in enumerate(self.columns):
            label = QtGui.QLabel(column.title())
            self.labels[column] = label
            self.result_layout.addWidget(label, index+1, 0)
            text_box = QtGui.QLineEdit("0.0")
            self.text_boxes[column] = text_box
            self.result_layout.addWidget(text_box, index+1, 1)

        # This adds stretch to an empty column
        self.result_layout.setColumnStretch(2, 1)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addLayout(self.result_layout)
        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)
        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.filter_outliers, "filter_outliers")

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        self.draw()

    def draw(self):
        if not self.model.contacts:
            return

        df = self.model.dataframe
        if self.outlier_toggle:
            df = df[df["filtered"]==False]

        contact_group = df.groupby("contact_label")
        if self.contact_label in contact_group.groups:
            data = contact_group.get_group(self.contact_label)
            for column in self.columns:
                self.text_boxes[column].setText("{:>6} +/- {:>5}".format("{:.2f}".format(np.mean(data[column].dropna())),
                                                                        "{:.2f}".format(np.std(data[column].dropna()))))


    def clear_cached_values(self):
        # Put the screen to black
        for column, text_box in self.text_boxes.items():
            text_box.setText("")

    def resizeEvent(self, event=None):
        pass

