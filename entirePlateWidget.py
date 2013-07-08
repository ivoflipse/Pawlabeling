from PyQt4.QtCore import *
from PyQt4.QtGui import *
import utility

class EntirePlateWidget(QWidget):
    def __init__(self, degree, size, parent = None):
        super(EntirePlateWidget, self).__init__(parent)
        self.parent = parent
        self.resize(size[0], size[1])
        self.layout = QVBoxLayout(self)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.layout.addWidget(self.view)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        # This pen is used to draw the polygons
        self.pen = QPen(Qt.white)
        # I can also draw with a brush
        self.brush = QBrush(Qt.white)
        # A cache to store the polygons of the previous frame
        self.previouspolygons = []
        self.bounding_boxes = []
        self.current_box = None
        self.gait_lines = []
        self.colors = [
                      QColor(Qt.green),
                      QColor(Qt.darkGreen),
                      QColor(Qt.red),
                      QColor(Qt.darkRed),
                      QColor(Qt.grey),
                      QColor(Qt.white),
                      QColor(Qt.yellow),
                      ]

        self.degree = degree
        self.imageCT = utility.ImageColorTable()
        self.color_table = self.imageCT.create_colortable()

    def newMeasurement(self, measurement):
        # Clear the bounding boxes + the line
        self.clear_bounding_box()
        self.clear_gait_line()
        # Update the measurement
        self.measurement = measurement
        self.height, self.width, self.numFrames = self.measurement.shape
        self.nmax = self.measurement.max()
        self.changeFrame(frame=-1)

        #self.cop_x, self.cop_y = utility.calculate_cop(self.measurement)

    def newPaws(self, paws):
        # Update the paws
        self.paws = paws
        # TODO shouldn't this be run by update blabla in mainWidget?
        #for paw in self.paws:
        #    self.draw_bounding_box(paw, paw_label = -2)
        self.draw_gait_line()

    def changeFrame(self, frame):
        # Set the frame
        self.frame = frame
        if frame == -1:
            self.data = self.measurement.max(axis=2).T
        else:
            # Slice out the data from the measurement
            self.data = self.measurement[:, :, self.frame].T
        # Update the pixmap
        self.image.setPixmap(utility.getQPixmap(self.data, self.degree, self.nmax, self.color_table))

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
        self.bboxpen = QPen(color)
        self.bboxpen.setWidth(3)

        if paw_label == -1:
            current_paw = 0.5
        else:
            current_paw = 0

        polygon = QPolygonF([QPointF((paw.totalminx - current_paw) * self.degree, (paw.totalminy - current_paw) * self.degree),
                             QPointF((paw.totalmaxx + current_paw) * self.degree, (paw.totalminy - current_paw) * self.degree),
                             QPointF((paw.totalmaxx + current_paw) * self.degree, (paw.totalmaxy + current_paw) * self.degree),
                             QPointF((paw.totalminx - current_paw) * self.degree, (paw.totalmaxy + current_paw) * self.degree)])

        self.bounding_boxes.append(self.scene.addPolygon(polygon, self.bboxpen))

    def update_bounding_boxes(self, paw_labels, current_paw_index):
        self.clear_bounding_box()

        for index, paw_label in paw_labels.items():
            # Mark unlabeled paws white if they're not the current paw
            if index != current_paw_index and paw_label == -1:
                paw_label = -2

            self.draw_bounding_box(self.paws[index], paw_label)
            if current_paw_index == index:
                self.draw_bounding_box(self.paws[index], paw_label=-1)


    def draw_gait_line(self):
        self.gait_line_pen = QPen(Qt.white)
        self.gait_line_pen.setWidth(2)
        self.gait_line_pen.setColor(Qt.white)

        self.clear_gait_line()

        for index in range(1, len(self.paws)):
            prevPaw = self.paws[index-1]
            curPaw = self.paws[index]
            polygon = QPolygonF([QPointF(prevPaw.totalcentroid[0] * self.degree, prevPaw.totalcentroid[1] * self.degree),
                                 QPointF(curPaw.totalcentroid[0] * self.degree, curPaw.totalcentroid[1] * self.degree)])
            self.gait_lines.append(self.scene.addPolygon(polygon, self.gait_line_pen))

        # It seems that COP is really a poor indicator in most cases, unless perhaps I can use the shape
        # points = []
        # for cop_x, cop_y in zip(self.cop_x, self.cop_y):
        #     points.append(QPointF(cop_y * self.degree, cop_x * self.degree))
        #
        # polygon = QPolygonF(points)
        # self.gait_lines.append(self.scene.addPolygon(polygon, self.gait_line_pen))




