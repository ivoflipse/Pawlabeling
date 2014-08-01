import logging
from collections import defaultdict
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pubsub import pub
from ...functions import utility
from ...settings import settings
from ...models import model


class GaitDiagramWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(GaitDiagramWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Gait Diagram")
        self.parent = parent
        self.active = False

        self.gait_diagram = GaitDiagramView(self, "Gait Diagram")

        self.gait_diagram_layout = QtGui.QVBoxLayout()
        self.gait_diagram_layout.addWidget(self.gait_diagram)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.gait_diagram_layout)
        self.setLayout(self.main_layout)

        pub.subscribe(self.change_frame, "analysis.change_frame")
        pub.subscribe(self.active_widget, "active_widget")

    def change_frame(self, frame):
        self.gait_diagram.change_frame(frame)

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            progress = 0
            pub.sendMessage("update_progress", progress=progress)
            self.gait_diagram.draw()
            pub.sendMessage("update_progress", progress=100)


class GaitDiagramView(QtGui.QWidget):
    def __init__(self, parent, label):
        super(GaitDiagramView, self).__init__(parent)
        label_font = settings.settings.label_font()
        self.label = QtGui.QLabel(label)
        self.label.setFont(label_font)
        self.parent = parent
        self.model = model.model
        self.degree = settings.settings.interpolation_results()
        self.colors = settings.settings.colors
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

        self.frame = -1
        self.length = 0
        self.ratio = 1
        self.outlier_toggle = False
        self.average_toggle = False

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        # This pen is used to draw the polygons
        self.pen = QtGui.QPen(Qt.white)
        # I can also draw with a brush
        self.brush = QtGui.QBrush(Qt.white)
        self.bounding_boxes = []
        self.gait_lines = []

        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)  # figsize=(10.0, 5.0)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)

        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(0)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view, stretch=2)
        self.main_layout.addWidget(self.canvas, stretch=3)
        self.setLayout(self.main_layout)

        pub.subscribe(self.draw, "put_measurement")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")

    def draw(self):
        self.clear_cached_values()
        self.model.get_measurement_data()
        self.n_max = self.model.measurement.maximum_value
        self.update_entire_plate()
        for index, contact in enumerate(self.model.contacts[self.model.measurement_name]):
            self.draw_bounding_box(contact, current_contact=False)
        if not self.gait_lines:
            self.draw_gait_line()
        self.update_gait_diagram()
        self.resizeEvent()

    def update_entire_plate(self):
        if self.frame == -1:
            self.data = self.model.measurement_data.max(axis=2).T
        else:
            self.data = self.model.measurement_data[:, :, self.frame].T
        self.length = self.model.measurement_data.shape[2]

        # Update the pixmap
        self.pixmap = utility.get_qpixmap(self.data, self.degree, self.n_max, self.color_table)
        self.image.setPixmap(self.pixmap)

    def update_gait_diagram(self):
        if not self.model.contacts:
            return

        self.clear_axes()
        na = False

        for contact in self.model.contacts[self.model.measurement_name]:
            min_z = contact.min_z
            length = contact.length

            contact_label = contact.contact_label
            if contact_label < 0:
                if settings.__human__:
                    contact_label = 2
                else:
                    contact_label = 4
                na = True

            self.axes.barh(bottom=contact_label, left=float(min_z), width=length, height=0.5,
                           align='center', color=settings.settings.matplotlib_color[contact_label])

        self.axes.set_xlim([0, self.model.measurement.number_of_frames])
        if na:
            if settings.__human__:
                self.axes.set_yticks(range(0, 2))
                self.axes.set_yticklabels(['Left', 'Right', 'NA'])
            else:
                self.axes.set_yticks(range(0, 5))
                self.axes.set_yticklabels(['Left Front', 'Left Hind', 'Right Front', 'Right Hind', 'NA'])
        else:

            if settings.__human__:
                self.axes.set_yticks(range(0, 2))
                self.axes.set_yticklabels(['Left', 'Right'])
            else:
                self.axes.set_yticks(range(0, 4))
                self.axes.set_yticklabels(['Left Front', 'Left Hind', 'Right Front', 'Right Hind'])
        self.axes.set_xlabel('Frames Since Beginning of Measurement')
        self.axes.yaxis.grid(True)
        self.axes.set_title('Periods of Contacts')

        self.vertical_line = self.axes.axvline(linewidth=4, color='r')
        self.vertical_line.set_xdata(self.frame)
        self.canvas.draw()

    def change_frame(self, frame):
        self.frame = frame
        if self.frame < self.length:
            self.update_entire_plate()
            self.vertical_line.set_xdata(self.frame)
            self.canvas.draw_idle()

    def clear_axes(self):
        self.axes.cla()
        self.canvas.draw()

    def clear_cached_values(self):
        self.clear_axes()
        self.clear_bounding_box()
        self.clear_gait_line()
        self.frame = -1
        self.data = np.zeros((64, 256))
        # Put the screen to black
        self.image.setPixmap(utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table))

    def clear_bounding_box(self):
        # Remove the old ones and redraw
        for box in self.bounding_boxes:
            self.scene.removeItem(box)
        self.bounding_boxes = []

    def clear_gait_line(self):
        # Remove the gait line
        for line in self.gait_lines:
            self.scene.removeItem(line)
        self.gait_lines = []

    def draw_bounding_box(self, contact, current_contact):
        if current_contact:
            current_contact = 0.5
            color = self.colors[-1]
        else:
            current_contact = 0
            color = self.colors[contact.contact_label]

        self.bounding_box_pen = QtGui.QPen(color)
        self.bounding_box_pen.setWidth(10)

        polygon = QtGui.QPolygonF(
            [QtCore.QPointF((contact.min_x - current_contact) * self.degree,
                            (contact.min_y - current_contact) * self.degree),
             QtCore.QPointF((contact.max_x + current_contact) * self.degree,
                            (contact.min_y - current_contact) * self.degree),
             QtCore.QPointF((contact.max_x + current_contact) * self.degree,
                            (contact.max_y + current_contact) * self.degree),
             QtCore.QPointF((contact.min_x - current_contact) * self.degree,
                            (contact.max_y + current_contact) * self.degree)])

        bounding_box = self.scene.addPolygon(polygon, self.bounding_box_pen)
        bounding_box.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
        self.bounding_boxes.append(bounding_box)
        self.resizeEvent()

    def draw_gait_line(self):
        self.gait_line_pen = QtGui.QPen(Qt.white)
        self.gait_line_pen.setWidth(5)
        self.gait_line_pen.setColor(Qt.white)

        for index in xrange(1, len(self.model.contacts[self.model.measurement_name])):
            prev_contact = self.model.contacts[self.model.measurement_name][index - 1]
            cur_contact = self.model.contacts[self.model.measurement_name][index]
            polygon = QtGui.QPolygonF(
                [QtCore.QPointF((prev_contact.min_x + (prev_contact.width/2)) * self.degree,
                                (prev_contact.min_y + (prev_contact.height/2)) * self.degree),
                 QtCore.QPointF((cur_contact.min_x + (cur_contact.width/2)) * self.degree,
                                (cur_contact.min_y + (cur_contact.height/2)) * self.degree)])
            gait_line = self.scene.addPolygon(polygon, self.gait_line_pen)
            gait_line.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
            self.gait_lines.append(gait_line)
        self.resizeEvent()

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width() / float(item_size.width()),
                    self.view.viewport().height() / float(item_size.height()))

        if abs(1 - ratio) > 0.1:
            # Store the ratio and use it to draw the bounding boxes
            self.ratio = self.ratio * ratio
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            for item in self.bounding_boxes:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            for item in self.gait_lines:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.centerOn(self.image)