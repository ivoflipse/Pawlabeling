from collections import defaultdict

from PySide import QtGui
from PySide.QtCore import Qt
import numpy as np

from functions import utility
from settings import configuration
import logging

class PawsWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(PawsWidget, self).__init__(parent)
        self.parent = parent

        self.left_front = PawWidget(self, label="Left Front")
        self.left_hind = PawWidget(self, label="Left Hind")
        self.right_front = PawWidget(self,label="Right Front")
        self.right_hind = PawWidget(self,label="Right Hind")
        self.current_paw = PawWidget(self, label="")

        self.paws_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
            -1: self.current_paw
        }

        self.logger = logging.getLogger("logger")

        self.paw_dict = configuration.paw_dict
        # This sets every widget to a zero image and initializes paws
        self.clear_paws()

        self.left_paws_layout = QtGui.QVBoxLayout()
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(self.left_hind)
        self.current_paw_layout = QtGui.QVBoxLayout()
        self.current_paw_layout.addStretch(1)
        self.current_paw_layout.addWidget(QtGui.QLabel("Current Paw"))
        self.current_paw_layout.addWidget(self.current_paw)
        self.current_paw_layout.setStretchFactor(self.current_paw, 3)
        self.current_paw_layout.addStretch(1)
        self.right_paws_layout = QtGui.QVBoxLayout()
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_paws_layout)
        self.main_layout.addLayout(self.current_paw_layout)
        self.main_layout.addLayout(self.right_paws_layout)
        self.setLayout(self.main_layout)

    # How do I tell which measurement we're at?
    def update_paws(self, paw_labels, paw_data, average_data, current_paw_index, current_measurement):
        # Clear the paws, so we can draw new ones
        self.clear_paws()

        # Make a copy
        from copy import deepcopy
        self.average_data = deepcopy(average_data)
        # Group all the data per paw
        data_array = defaultdict(list)
        for measurement_name, data_list in paw_data.items():
            for paw_label, data in zip(paw_labels[measurement_name].values(), data_list):
                if paw_label >= 0:
                    data_array[paw_label].append(data)
                    normalized_data = utility.normalize_paw_data(data)
                    self.average_data[paw_label].append(normalized_data)  # I wonder if this mutates the list...

        # Do I need to cache information so I can use it later on? Like in predict_label?
        for paw_label, average_list in self.average_data.items():
            data = data_array[paw_label]
            widget = self.paws_list[paw_label]
            # This can sometimes be empty, if things are reset
            if data:
                widget.update(data, average_list)
            else:
                widget.clear_paws()

        # Update the current paw widget
        widget = self.paws_list[-1]
        current_paw = paw_data[current_measurement][current_paw_index]
        normalized_current_paw = utility.normalize_paw_data(current_paw)
        # These are put in lists, because we try to iterate through them
        widget.update([current_paw], [normalized_current_paw])

        try:
            self.predict_label()
        except Exception as e:
            self.logger("Couldn't predict the labels. Exception: {}".format(e))


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
        for paw_label, paw in list(self.paws_list.items()):
            # Skip comparing with yourself
            if paw_label == -1:
                continue
            pressures.append(paw.max_pressure)
            surfaces.append(paw.mean_surface)
            durations.append(paw.mean_duration)
            data_list.append(paw.data)

        # For each value calculate how much % it varies
        if all([pressure, surface, duration, data_list]):
            percentages_pressures = [np.sqrt((p - pressure) ** 2) / pressure for p in pressures]
            percentages_surfaces = [np.sqrt((s - surface) ** 2) / surface for s in surfaces]
            percentages_durations = [np.sqrt((d - duration) ** 2) / duration for d in durations]
            percentages_data = [np.sum(np.sqrt((d - data)**2)) / np.sum(np.sum(data)) for d in data_list]
            #percentages_data = [np.sum(np.sqrt((d - data) ** 2)) for d in data_list]
            results = []
            for p, s, d, d2 in zip(percentages_pressures, percentages_surfaces, percentages_durations,
                                   percentages_data):
                results.append(p + s + d + d2)

            best_result = np.argmin(results)
            current_paw.label_prediction.setText("{}".format(self.paw_dict[best_result]))


    def update_n_max(self, n_max):
        for paw_label, paw in list(self.paws_list.items()):
            paw.n_max = n_max

    def clear_paws(self):
        for paw_label, paw in list(self.paws_list.items()):
            paw.clear_paws()


class PawWidget(QtGui.QWidget):
    def __init__(self, parent, label):
        super(PawWidget, self).__init__(parent)
        self.parent = parent
        self.degree = configuration.interpolation_paws_widget
        self.n_max = 0
        self.label = label
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 100
        self.my = 100
        self.data = np.zeros((self.mx, self.my))
        self.data_list = []
        self.average_data_list = []

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.max_pressure = float("inf")
        self.mean_duration = float("inf")
        self.mean_surface = float("inf")

        self.label_prediction = QtGui.QLabel(self)
        self.max_pressure_label = QtGui.QLabel(self)
        self.mean_duration_label = QtGui.QLabel(self)
        self.mean_surface_label = QtGui.QLabel(self)

        self.label_prediction.setText("{}".format(self.label))
        self.max_pressure_label.setText("{} N".format(0 if self.max_pressure == float("inf") else self.max_pressure))
        self.mean_duration_label.setText(
            "{} frames".format(0 if self.mean_duration == float("inf") else self.mean_duration))
        self.mean_surface_label.setText(
            "{} pixels".format(0 if self.mean_surface == float("inf") else self.mean_surface))

        self.number_layout = QtGui.QVBoxLayout()
        self.number_layout.addWidget(self.label_prediction)
        self.number_layout.addWidget(self.max_pressure_label)
        self.number_layout.addWidget(self.mean_duration_label)
        self.number_layout.addWidget(self.mean_surface_label)
        self.number_layout.addStretch(1)

        self.main_layout = QtGui.QHBoxLayout(self)
        self.main_layout.addWidget(self.view)
        self.main_layout.addLayout(self.number_layout)

        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

    def update(self, data_list, average_data):
        # Calculate an average paw from the list of arrays
        self.data_list = data_list
        self.average_data_list = average_data
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

        if len(mean_data_list) > 1:
            data = np.array(mean_data_list).mean(axis=0)
        else:
            data = np.array(mean_data_list[0])

        # Make sure the paws are facing upright
        self.data = np.rot90(np.rot90(data))
        # Only display the non-zero part, regardless of its size
        x, y = np.nonzero(self.data)
        sliced_data = self.data
        if len(x):  # This won't work for empty array's
            # This might off course go out of bounds some day
            min_x = np.min(x) - 2
            max_x = np.max(x) + 2
            min_y = np.min(y) - 2
            max_y = np.max(y) + 2
            sliced_data = self.data[min_x:max_x, min_y:max_y]

        # Flip around the vertical axis (god knows why)
        sliced_data = sliced_data[:, ::-1]
        self.pixmap = utility.get_QPixmap(sliced_data, self.degree, self.n_max, self.color_table, interpolation="cubic")
        self.image.setPixmap(self.pixmap)

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

    def resizeEvent(self, event):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width()/float(item_size.width()),
                    self.view.viewport().height()/float(item_size.height()))

        if abs(1-ratio) > 0.1:
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)
