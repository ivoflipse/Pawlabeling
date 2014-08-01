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



class AsymmetryWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(AsymmetryWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Asymmetry")
        self.parent = parent
        self.active = False

        self.asymmetry_front = AsymmetryView(self, "Asymmetry Front", compare=[[0],[2]])
        self.asymmetry_hind = AsymmetryView(self, "Asymmetry Hind", compare=[[1],[3]])
        self.asymmetry_pt = AsymmetryView(self, "Asymmetry PT", compare=[[0,2],[1,3]])

        self.asymmetry_list = [self.asymmetry_front,
                               self.asymmetry_hind,
                               self.asymmetry_pt]

        self.asymmetry_layout = QtGui.QHBoxLayout()
        self.asymmetry_layout.addWidget(self.asymmetry_front)
        self.asymmetry_layout.addWidget(self.asymmetry_hind)
        self.asymmetry_layout.addWidget(self.asymmetry_pt)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.asymmetry_layout)
        self.setLayout(self.main_layout)

        pub.subscribe(self.active_widget, "active_widget")

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            progress = 0
            pub.sendMessage("update_progress", progress=progress)
            for view in self.asymmetry_list:
                view.draw()
            pub.sendMessage("update_progress", progress=100)


class AsymmetryView(QtGui.QWidget):
    def __init__(self, parent, label, compare):
        super(AsymmetryView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.parent = parent
        self.model = model.model
        self.compare = compare

        self.frame = -1
        self.length = 0
        self.ratio = 1
        self.outlier_toggle = False
        self.average_toggle = False

        self.labels = {}
        self.text_boxes = {}

        self.columns = ["peak_force","peak_pressure","peak_surface","vertical_impulse",
                        "stance_duration","stance_percentage","step_duration","step_length"]

        self.asi_layout = QtGui.QGridLayout()
        self.asi_layout.setSpacing(10)

        self.asi_layout.addWidget(self.label, 0, 0, columnSpan=1)

        for index, column in enumerate(self.columns):
            label = QtGui.QLabel(column.title())
            self.labels[column] = label
            self.asi_layout.addWidget(label, index+1, 0)
            text_box = QtGui.QLineEdit("0.0")
            self.text_boxes[column] = text_box
            self.asi_layout.addWidget(text_box, index+1, 1)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addLayout(self.asi_layout)
        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)
        pub.subscribe(self.clear_cached_values, "clear_cached_values")

    def draw(self):
        if not self.model.contacts:
            return

        asi = defaultdict(list)
        # I probably should calculate this in the model as well
        for measurement_id, measurement_group in self.model.dataframe.groupby("measurement_id"):
            contact_group = measurement_group.groupby("contact_label")

            # Check if all the compare contacts are present
            present = True
            for l in self.compare[0]:
                if l not in contact_group.groups:
                    present = False
            for r in self.compare[1]:
                if r not in contact_group.groups:
                    present = False

            if not present:
                continue

            for column in self.columns:
                left = 0.
                right = 0.
                for l in self.compare[0]:
                    if l in contact_group.groups:
                        left += np.mean(contact_group.get_group(l)[column].dropna())
                for r in self.compare[1]:
                    if r in contact_group.groups:
                        right += np.mean(contact_group.get_group(r)[column].dropna())

                # Somehow one or the other can have an opposite sign, so make them absolute
                if column == "step_length":
                    left = abs(left)
                    right = abs(right)
                # Only calculate the ASI if we've progressed from the default
                if left > 0 and right > 0:
                    asi[column].append(calculations.asymmetry_index(left, right))

        for column in self.columns:
            #print column, asi[column]
            self.text_boxes[column].setText("{:>6} +/- {:>5}".format("{:.2f}".format(np.mean(asi[column])),
                                                                    "{:.2f}".format(np.std(asi[column]))))



    def clear_cached_values(self):
        # Put the screen to black
        for column, text_box in self.text_boxes.items():
            text_box.setText("")

    def resizeEvent(self, event=None):
        pass

