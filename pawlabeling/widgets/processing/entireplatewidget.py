import os
import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from pawlabeling.functions import utility, gui
from pawlabeling.settings import settings
from pawlabeling.models import model


class EntirePlateWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(EntirePlateWidget, self).__init__(parent)
        self.parent = parent
        self.model = model.model
        self.ratio = 1
        self.num_frames = 0

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
        self.measurement_name = ""

        self.settings = settings.settings
        self.colors = self.settings.colors
        self.degree = self.settings.interpolation_entire_plate()
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.setMinimumHeight(self.settings.entire_plate_widget_height())

        # Create a slider
        self.slider = QtGui.QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(-1)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.slider_moved)
        self.slider_text = QtGui.QLabel(self)
        self.slider_text.setText("Frame: -1")

        self.slider_layout = QtGui.QHBoxLayout()
        self.slider_layout.addWidget(self.slider)
        self.slider_layout.addWidget(self.slider_text)

        self.layout = QtGui.QVBoxLayout(self)
        self.layout.addWidget(self.view)
        self.layout.addLayout(self.slider_layout)

        # Add application-wide shortcuts
        self.slide_to_left_action = gui.create_action(text="Slide Left",
                                                      shortcut=QtGui.QKeySequence(QtCore.Qt.Key_Left),
                                                      icon=QtGui.QIcon(
                                                          os.path.join(os.path.dirname(__file__),
                                                                       "../images/arrow_left.png")),
                                                      tip="Move the slider to the left",
                                                      checkable=False,
                                                      connection=self.slide_to_left
        )

        self.slide_to_right_action = gui.create_action(text="Slide Right",
                                                       shortcut=QtGui.QKeySequence(QtCore.Qt.Key_Right),
                                                       icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                     "../images/arrow_right.png")),
                                                       tip="Move the slider to the right",
                                                       checkable=False,
                                                       connection=self.slide_to_right
        )

        self.fast_backward_action = gui.create_action(text="Fast Back",
                                                      shortcut=QtGui.QKeySequence.MoveToNextWord,
                                                      #QKeySequence(Qt.CTRL + Qt.Key_Left),
                                                      icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                    "../images/arrow_left.png")),
                                                      tip="Move the slider to the left faster",
                                                      checkable=False,
                                                      connection=self.fast_backward
        )

        self.fast_forward_action = gui.create_action(text="Fast Forward",
                                                     shortcut=QtGui.QKeySequence.MoveToPreviousWord,
                                                     #QKeySequence(Qt.CTRL + Qt.Key_Right),
                                                     icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                                   "../images/arrow_right.png")),
                                                     tip="Move the slider to the right faster",
                                                     checkable=False,
                                                     connection=self.fast_forward
        )

        # Not adding the forward/backward buttons to the toolbar
        self.non_toolbar_actions = [self.slide_to_left_action, self.slide_to_right_action,
                                    self.fast_backward_action, self.fast_forward_action]

        for action in self.non_toolbar_actions:
            action.setShortcutContext(Qt.ApplicationShortcut)  # WidgetWithChildrenShortcut

        # TODO I might have to unsubscribe these as well...
        pub.subscribe(self.update_measurement, "update_measurement")
        pub.subscribe(self.update_measurement_data, "update_measurement_data")
        pub.subscribe(self.update_contacts, "update_contacts")
        pub.subscribe(self.update_contacts, "updated_current_contact")
        pub.subscribe(self.clear_cached_values, "clear_cached_values")

    def update_measurement(self):
        self.clear_gait_line()

        self.n_max = self.model.measurement.maximum_value
        self.height = self.model.measurement.number_of_rows
        self.width = self.model.measurement.number_of_columns
        self.num_frames = self.model.measurement.number_of_frames
        self.measurement_name = self.model.measurement.measurement_name

    def fast_backward(self):
        self.change_slider(-1, fast=True)

    def fast_forward(self):
        self.change_slider(1, fast=True)

    def slide_to_left(self, fast=False):
        self.change_slider(-1, fast)

    def slide_to_right(self, fast=False):
        self.change_slider(1, fast)

    def change_slider(self, frame_diff, fast=False):
        if fast:
            frame_diff *= 10

        new_frame = self.frame + frame_diff
        if new_frame > self.num_frames:
            new_frame = self.num_frames % new_frame

        self.slider.setValue(new_frame)

    def slider_moved(self, frame):
        self.slider_text.setText("Frame: {}".format(frame))
        self.frame = frame
        self.change_frame(self.frame)

    def update_measurement_data(self):
        # Update the measurement
        self.measurement_data = self.model.measurement_data
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.num_frames - 1)
        # Reset the frame slider
        self.slider.setValue(-1)
        self.update_entire_plate()

    def update_contacts(self):
        if not self.gait_lines:
            self.draw_gait_line()

        self.clear_bounding_box()
        for index, contact in enumerate(self.model.contacts[self.measurement_name]):
            self.draw_bounding_box(contact, contact.contact_label)
            if self.model.current_contact_index == index:
                self.draw_bounding_box(contact, contact_label=-1)
        self.resizeEvent()

    def change_frame(self, frame):
        # Set the frame
        self.frame = frame
        self.update_entire_plate()

    def update_entire_plate(self):
        if self.frame == -1:
            self.data = self.measurement_data.max(axis=2).T
        else:
            # Slice out the measurement_data from the measurement
            self.data = self.measurement_data[:, :, self.frame].T

        # Update the pixmap
        self.pixmap = utility.get_qpixmap(self.data, self.degree, self.n_max, self.color_table)
        self.image.setPixmap(self.pixmap)
        self.resizeEvent()

    def clear_cached_values(self):
        self.clear_bounding_box()
        self.clear_gait_line()
        self.num_frames = 0
        self.data = np.zeros((15, 15))
        self.frame = -1

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

    def draw_bounding_box(self, contact, contact_label):
        color = self.colors[contact_label]
        self.bounding_box_pen = QtGui.QPen(color)
        self.bounding_box_pen.setWidth(3)

        if contact.contact_label == -1:
            current_contact = 0.5
        else:
            current_contact = 0

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
        self.gait_line_pen.setWidth(2)
        self.gait_line_pen.setColor(Qt.white)

        for index in xrange(1, len(self.model.contacts[self.measurement_name])):
            prev_contact = self.model.contacts[self.measurement_name][index - 1]
            cur_contact = self.model.contacts[self.measurement_name][index]
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


