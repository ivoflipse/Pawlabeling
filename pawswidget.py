#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
import utility


class PawsWidget(QWidget):
    def __init__(self, parent, degree, n_max):
        super(PawsWidget, self).__init__(parent)
        self.parent = parent
        self.degree = degree

        self.left_front = PawWidget(self, degree, n_max, label="LF")
        self.left_hind = PawWidget(self, degree, n_max, label="LH")
        self.right_front = PawWidget(self, degree, n_max, label="RF")
        self.right_hind = PawWidget(self, degree, n_max, label="RH")
        self.current_paw = PawWidget(self, degree, n_max, label="")

        self.paws_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
            -1: self.current_paw
        }

        self.paw_dict = {
            0: "LF",
            1: "LH",
            2: "RF",
            3: "RH",
            -3: "Invalid",
            -2: "-1", # I've changed this
            -1: "-1"
        }

        # This sets every widget to a zero image and initializes paws
        self.clear_paws()

        self.left_paws_layout = QVBoxLayout()
        self.left_paws_layout.addWidget(QLabel("Left Front"))
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(QLabel("Left Hind"))
        self.left_paws_layout.addWidget(self.left_hind)
        self.current_paw_layout = QVBoxLayout()
        self.current_paw_layout.addWidget(QLabel("Current Paw"))
        self.current_paw_layout.addWidget(self.current_paw)
        self.right_paws_layout = QVBoxLayout()
        self.right_paws_layout.addWidget(QLabel("Right Front"))
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(QLabel("Right Hind"))
        self.right_paws_layout.addWidget(self.right_hind)

        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.left_paws_layout)
        self.main_layout.addLayout(self.current_paw_layout)
        self.main_layout.addLayout(self.right_paws_layout)
        self.setLayout(self.main_layout)

    # self.paws_widget.update_current_paw(self.paw_labels, self.current_paw_index, self.paw_data)
    def update_paws(self, paw_labels, current_paw_index, paw_data, average_data):
        # Clear the paws, so we can draw new ones
        # TODO only update if the information has changed
        self.clear_paws()
        for index, paw in enumerate(paw_data):
            average_paw = average_data[index]
            paw_label = paw_labels[index]
            # We don't do anything with unlabeled paws that aren't selected or invalid
            if paw_label < -1:
                continue
                # If we do have a label, but we have selected it, update the current_paw too
            if current_paw_index == index and paw_label != -1:
                self.paws[-1] = [[paw], [average_paw]]

            if paw_label not in self.paws:
                self.paws[paw_label] = [], []
                # Add the data to the paws dictionary
            self.paws[paw_label][0].append(paw)
            self.paws[paw_label][1].append(average_paw)

        # Update the widgets
        for paw_label, data_list in self.paws.items():
            widget = self.paws_list.get(paw_label, None)
            # If -2 or -3 there will be no widget
            if widget:
                widget.update(data_list)

        try:
            self.predict_label()
        except Exception, e:
            print e

    def predict_label(self):
        current_paw = self.paws_list[-1]
        # If there's no data, we can quit
        if current_paw.max_pressure == float("inf"):
            return

        pressure = current_paw.max_pressure
        surface = current_paw.mean_surface
        duration = current_paw.mean_duration
        data = current_paw.data

        pressures = []
        surfaces = []
        durations = []
        data_list = []
        # Then iterate through the other paws
        for paw_label, paw in self.paws_list.items():
            # Skip comparing with yourself
            if paw_label == -1:
                continue
            pressures.append(paw.max_pressure)
            surfaces.append(paw.mean_surface)
            durations.append(paw.mean_duration)
            data_list.append(paw.data)

        # For each value calculate how much % it varies
        # TODO this has an obvious risk of divide by zero
        if all([pressure, surface, duration, data_list]):
            percentages_pressures = [np.sqrt((p - pressure) ** 2) / pressure for p in pressures]
            percentages_surfaces = [np.sqrt((s - surface) ** 2) / surface for s in surfaces]
            percentages_durations = [np.sqrt((d - duration) ** 2) / duration for d in durations]
            #percentages_data = [np.sum(np.sqrt((d - data)**2)) / np.sum(np.sum(data)) for d in data_list]
            percentages_data = [np.sum(np.sqrt((d - data) ** 2)) for d in data_list]
            results = []
            for p, s, d, d2 in zip(percentages_pressures, percentages_surfaces, percentages_durations,
                                   percentages_data):
                results.append(p + s + d + d2)
                # TODO I'm also not so satisfied with this heuristic, though it might get better with more data
            best_result = np.argmin(results)
            current_paw.label_prediction.setText("{}".format(self.paw_dict[best_result]))


    def update_n_max(self, n_max):
        for paw_label, paw in self.paws_list.items():
            paw.n_max = n_max

    def update_shape(self, mx, my):
        for paw_label, paw in self.paws_list.items():
            paw.mx = mx
            paw.my = my

        self.clear_paws()

    def clear_paws(self):
        self.paws = {}
        for paw_label, paw in self.paws_list.items():
            paw.clear_paws()


class PawWidget(QWidget):
    def __init__(self, parent, degree, n_max, label):
        super(PawWidget, self).__init__(parent)
        self.parent = parent
        self.degree = degree
        self.n_max = n_max
        self.label = label
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 15
        self.my = 15
        self.data = np.zeros((self.mx, self.my))
        self.data_list = []
        self.average_data_list = []

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setGeometry(0, 0, 100, 100)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.max_pressure = float("inf")
        self.mean_duration = float("inf")
        self.mean_surface = float("inf")

        self.label_prediction = QLabel(self)
        self.max_pressure_label = QLabel(self)
        self.mean_duration_label = QLabel(self)
        self.mean_surface_label = QLabel(self)

        self.label_prediction.setText("{}".format(self.label))
        self.max_pressure_label.setText("{} N".format(0 if self.max_pressure == float("inf") else self.max_pressure))
        self.mean_duration_label.setText(
            "{} frames".format(0 if self.mean_duration == float("inf") else self.mean_duration))
        self.mean_surface_label.setText(
            "{} pixels".format(0 if self.mean_surface == float("inf") else self.mean_surface))

        self.number_layout = QVBoxLayout()
        self.number_layout.addWidget(self.label_prediction)
        self.number_layout.addWidget(self.max_pressure_label)
        self.number_layout.addWidget(self.mean_duration_label)
        self.number_layout.addWidget(self.mean_surface_label)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.view)
        self.main_layout.addLayout(self.number_layout)
        self.setLayout(self.main_layout)

    def update(self, data_list):
        # Calculate an average paw from the list of arrays
        self.data_list, self.average_data_list = data_list
        mean_data_list = []
        pressures = []
        surfaces = []
        durations = []
        for data, average_data in zip(self.data_list, self.average_data_list):
            mean_data_list.append(average_data)
            pressures.append(np.max(np.sum(np.sum(data, axis=0), axis=0)))
            x, y, z = data.shape
            durations.append(z)
            surfaces.append(np.max([np.count_nonzero(data[:, :, frame]) for frame in range(z)]))

        self.max_pressure = int(np.mean(pressures))
        self.mean_duration = int(np.mean(durations))
        self.mean_surface = int(np.mean(surfaces))

        self.max_pressure_label.setText("{} N".format(self.max_pressure))
        self.mean_duration_label.setText("{} frames".format(self.mean_duration))
        self.mean_surface_label.setText("{} pixels".format(self.mean_surface))

        # TODO this might not work so well
        data = np.array(mean_data_list).mean(axis=0)
        # Make sure the paws are facing upright
        self.data = np.rot90(np.rot90(data))
        self.image.setPixmap(utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table))

    def clear_paws(self):
        self.data = np.zeros((self.mx, self.my))
        self.data_list = []
        self.average_data_list = []
        # Put the screen to black
        self.image.setPixmap(utility.get_QPixmap(np.zeros((15, 15)), self.degree, self.n_max, self.color_table))
        self.max_pressure = float("inf")
        self.mean_duration = float("inf")
        self.mean_surface = float("inf")

        self.label_prediction.setText("{}".format(self.label))
        self.max_pressure_label.setText("{} N".format(0 if self.max_pressure == float("inf") else self.max_pressure))
        self.mean_duration_label.setText(
            "{} frames".format(0 if self.mean_duration == float("inf") else self.mean_duration))
        self.mean_surface_label.setText(
            "{} pixels".format(0 if self.mean_surface == float("inf") else self.mean_surface))