import numpy as np
from PySide import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pawlabeling.functions import utility, calculations

from pawlabeling.settings import configuration
from pawlabeling.functions.pubsub import pub


class ForceViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(ForceViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
        self.parent = parent

        self.left_front = PawView(self, label="Left Front", paw_label=0)
        self.left_hind = PawView(self, label="Left Hind", paw_label=1)
        self.right_front = PawView(self, label="Right Front", paw_label=2)
        self.right_hind = PawView(self, label="Right Hind", paw_label=3)

        self.paws_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
        }

        self.left_paws_layout = QtGui.QVBoxLayout()
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(self.left_hind)
        self.right_paws_layout = QtGui.QVBoxLayout()
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_paws_layout)
        self.main_layout.addLayout(self.right_paws_layout)
        self.setLayout(self.main_layout)


class PawView(QtGui.QWidget):
    def __init__(self, parent, label, paw_label):
        super(PawView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.paw_label = paw_label
        self.parent = parent
        self.n_max = 0
        self.frame = 0
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.x = 100
        self.y = 100
        self.active = False
        self.filtered = []
        self.outlier_toggle = False

        self.dpi = 100
        self.fig = Figure(figsize=(3.0, 2.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(0)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.canvas)
        self.main_layout.setStretchFactor(self.canvas, 3)
        self.setMinimumHeight(configuration.paws_widget_height)
        self.setLayout(self.main_layout)

        pub.subscribe(self.update_n_max, "update_n_max")
        pub.subscribe(self.change_frame, "analysis.change_frame")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.update, "analysis_results")
        pub.subscribe(self.check_active, "active_widget")
        pub.subscribe(self.filter_outliers, "filter_outliers")

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        self.clear_cached_values()
        self.draw()

    def check_active(self, widget):
        self.active = False
        # Check if I'm the active widget
        if self.parent == widget:
            self.active = True
            self.draw()

    def update_n_max(self, n_max):
        self.n_max = n_max

    def update(self, paws, average_data, results, max_results):
        self.forces = results[self.paw_label]["force"]
        self.max_duration = max_results["duration"]
        self.max_force = max_results["force"]
        self.filtered = results[self.paw_label]["filtered"]

        self.draw()

    def draw(self):
        if not self.forces:
            return

        self.clear_cached_values()
        interpolate_length = 100
        lengths = []

        if self.outlier_toggle:
            filtered = self.filtered
        else:
            filtered = []

        # The zero padding of leaving elements out is 'painful'
        force_over_time = np.zeros((len(self.forces)-len(filtered), interpolate_length))
        forces = [f for index, f in enumerate(self.forces) if index not in filtered]

        for index, force in enumerate(forces):
            force = np.pad(force, 1, mode="constant", constant_values=0)
            lengths.append(len(force))
            force_over_time[index, :] = calculations.interpolate_time_series(force, interpolate_length)
            self.axes.plot(calculations.interpolate_time_series(range(np.max(len(force))), interpolate_length),
                           force_over_time[index, :], alpha=0.5)

        mean_length = np.mean(lengths)
        interpolated_timeline = calculations.interpolate_time_series(range(int(mean_length)), interpolate_length)
        mean_force = np.mean(force_over_time, axis=0)
        std_force = np.std(force_over_time, axis=0)
        self.axes.plot(interpolated_timeline, mean_force, color="r", linewidth=3)
        self.axes.plot(interpolated_timeline, mean_force + std_force, color="r", linewidth=1)
        self.axes.fill_between(interpolated_timeline, mean_force - std_force, mean_force + std_force, facecolor="r",
                               alpha=0.5)
        self.axes.plot(interpolated_timeline, mean_force - std_force, color="r", linewidth=1)
        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(self.frame)
        self.axes.set_xlim([0, self.max_duration + 2])  # +2 because we padded the array
        self.axes.set_ylim([0, self.max_force * 1.2])
        self.canvas.draw()

    def change_frame(self, frame):
        self.frame = frame
        if self.active:
            self.vertical_line.set_xdata(self.frame)
            self.canvas.draw()

    def clear_cached_values(self):
        # Put the screen to black
        self.axes.cla()
        self.canvas.draw()
