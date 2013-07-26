import os
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from functions import utility, gui
from settings import configuration

class EntirePlateWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(EntirePlateWidget, self).__init__(parent)
        self.parent = parent
        #self.resize(configuration.entire_plate_widget_width, configuration.entire_plate_widget_height)

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        # This pen is used to draw the polygons
        self.pen = QtGui.QPen(Qt.white)
        # I can also draw with a brush
        self.brush = QtGui.QBrush(Qt.white)
        self.bounding_boxes = []
        self.gait_lines = []
        self.measurement_name = ""

        self.colors = configuration.colors
        self.degree = configuration.interpolation_entire_plate
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()

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
                                                                       "images/arrow-left-icon.png")),
                                                      tip="Move the slider to the left",
                                                      checkable=False,
                                                      connection=self.slide_to_left
        )

        self.slide_to_right_action = gui.create_action(text="Slide Right",
                                                       shortcut=QtGui.QKeySequence(QtCore.Qt.Key_Right),
                                                       icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                               "images/arrow-right-icon.png")),
                                                       tip="Move the slider to the right",
                                                       checkable=False,
                                                       connection=self.slide_to_right
        )

        self.fast_backward_action = gui.create_action(text="Fast Back",
                                                      shortcut=QtGui.QKeySequence.MoveToNextWord,#QKeySequence(Qt.CTRL + Qt.Key_Left),
                                                      icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                              "images/arrow-left-icon.png")),
                                                      tip="Move the slider to the left faster",
                                                      checkable=False,
                                                      connection=self.fast_backward
        )

        self.fast_forward_action = gui.create_action(text="Fast Forward",
                                                     shortcut=QtGui.QKeySequence.MoveToPreviousWord, #QKeySequence(Qt.CTRL + Qt.Key_Right),
                                                     icon=QtGui.QIcon(os.path.join(os.path.dirname(__file__),
                                                                             "images/arrow-right-icon.png")),
                                                     tip="Move the slider to the right faster",
                                                     checkable=False,
                                                     connection=self.fast_forward
        )

        # Not adding the forward/backward buttons to the toolbar
        self.non_toolbar_actions = [self.slide_to_left_action, self.slide_to_right_action,
                                    self.fast_backward_action, self.fast_forward_action]

        for action in self.non_toolbar_actions:
            action.setShortcutContext(Qt.ApplicationShortcut)  # WidgetWithChildrenShortcut

        # # Install an event filter
        # self.slider.installEventFilter(self)


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

    def new_measurement(self, measurement, measurement_name):
        # Update the measurement
        self.measurement = measurement
        self.measurement_name = measurement_name
        self.height, self.width, self.num_frames = self.measurement.shape
        self.n_max = self.measurement.max()
        self.change_frame(frame=-1)

        # Reset the frame slider
        self.slider.setValue(-1)
        # Update the slider, in case the shape of the file changes
        self.slider.setMaximum(self.num_frames - 1)

    def new_paws(self, paws):
        # Update the paws
        self.paws = paws

    def change_frame(self, frame):
        # Set the frame
        self.frame = frame
        if frame == -1:
            self.data = self.measurement.max(axis=2).T
        else:
            # Slice out the data from the measurement
            self.data = self.measurement[:, :, self.frame].T

        # Update the pixmap
        self.pixmap = utility.get_QPixmap(self.data, self.degree, self.n_max, self.color_table)
        self.image.setPixmap(self.pixmap)

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

    def draw_bounding_box(self, paw, paw_label):
        color = self.colors[paw_label]
        self.bounding_box_pen = QtGui.QPen(color)
        self.bounding_box_pen.setWidth(3)

        if paw_label == -1:
            current_paw = 0.5
        else:
            current_paw = 0

        polygon = QtGui.QPolygonF(
            [QtCore.QPointF((paw.total_min_x - current_paw) * self.degree, (paw.total_min_y - current_paw) * self.degree),
             QtCore.QPointF((paw.total_max_x + current_paw) * self.degree, (paw.total_min_y - current_paw) * self.degree),
             QtCore.QPointF((paw.total_max_x + current_paw) * self.degree, (paw.total_max_y + current_paw) * self.degree),
             QtCore.QPointF((paw.total_min_x - current_paw) * self.degree, (paw.total_max_y + current_paw) * self.degree)])

        self.bounding_boxes.append(self.scene.addPolygon(polygon, self.bounding_box_pen))

    def update_bounding_boxes(self, paw_labels, current_paw_index):
        self.clear_bounding_box()

        for index, paw_label in paw_labels.items():
            self.draw_bounding_box(self.paws[self.measurement_name][index], paw_label)
            if current_paw_index == index:
                self.draw_bounding_box(self.paws[self.measurement_name][index], paw_label=-1)


    def draw_gait_line(self):
        self.gait_line_pen = QtGui.QPen(Qt.white)
        self.gait_line_pen.setWidth(2)
        self.gait_line_pen.setColor(Qt.white)

        self.clear_gait_line()

        for index in range(1, len(self.paws[self.measurement_name])):
            prevPaw = self.paws[self.measurement_name][index - 1]
            curPaw = self.paws[self.measurement_name][index]
            polygon = QtGui.QPolygonF(
                [QtCore.QPointF(prevPaw.total_centroid[0] * self.degree, prevPaw.total_centroid[1] * self.degree),
                 QtCore.QPointF(curPaw.total_centroid[0] * self.degree, curPaw.total_centroid[1] * self.degree)])
            self.gait_lines.append(self.scene.addPolygon(polygon, self.gait_line_pen))


    # def resizeEvent(self, event):
    #     item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
    #     ratio = min(self.view.viewport().width()/float(item_size.width()),
    #                 self.view.viewport().height()/float(item_size.height()))
    #
    #     if abs(1-ratio) > 0.1:
    #         self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
    #         for item in self.bounding_boxes:
    #             item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
    #         for item in self.gait_lines:
    #             item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
    #         #self.view.fitInView(self.rect(), Qt.KeepAspectRatio)
    #         self.view.centerOn(self.image)


