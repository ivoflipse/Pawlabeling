import logging
import numpy as np
from PySide import QtGui, QtCore
from pubsub import pub
from pawlabeling.functions import utility, calculations
from pawlabeling.settings import settings
from pawlabeling.models import model


class CopViewWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(CopViewWidget, self).__init__(parent)
        self.label = QtGui.QLabel("Force View")
        self.parent = parent
        self.active = False

        self.left_front = ContactView(self, label="Left Front", contact_label=0)
        self.left_hind = ContactView(self, label="Left Hind", contact_label=1)
        self.right_front = ContactView(self, label="Right Front", contact_label=2)
        self.right_hind = ContactView(self, label="Right Hind", contact_label=3)

        self.contacts_list = {
            0: self.left_front,
            1: self.left_hind,
            2: self.right_front,
            3: self.right_hind,
        }

        self.left_contacts_layout = QtGui.QVBoxLayout()
        self.left_contacts_layout.addWidget(self.left_front)
        self.left_contacts_layout.addWidget(self.left_hind)
        self.right_contacts_layout = QtGui.QVBoxLayout()
        self.right_contacts_layout.addWidget(self.right_front)
        self.right_contacts_layout.addWidget(self.right_hind)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.left_contacts_layout)
        self.main_layout.addLayout(self.right_contacts_layout)
        self.setLayout(self.main_layout)

        pub.subscribe(self.change_frame, "analysis.change_frame")
        pub.subscribe(self.active_widget, "active_widget")

    def change_frame(self, frame):
        for contact_label, widget in self.contacts_list.iteritems():
            if self.active:
                widget.change_frame(frame)
            else:
                widget.frame = frame

    def active_widget(self, widget):
        self.active = False
        if self == widget:
            self.active = True
            progress = 0
            pub.sendMessage("update_progress", progress=progress)
            for contact_label, widget in self.contacts_list.iteritems():
                widget.draw()
                progress += 25
                pub.sendMessage("update_progress", progress=progress)
            pub.sendMessage("update_progress", progress=100)

class ContactView(QtGui.QWidget):
    def __init__(self, parent, label, contact_label):
        super(ContactView, self).__init__(parent)
        self.label = QtGui.QLabel(label)
        self.contact_label = contact_label
        self.parent = parent
        self.model = model.model
        self.settings = settings.settings
        self.degree = self.settings.interpolation_results()
        self.image_color_table = utility.ImageColorTable()
        self.color_table = self.image_color_table.create_color_table()
        self.mx = 1
        self.my = 1
        self.mz = 1
        self.min_x = 0
        self.max_x = self.mx
        self.min_y = 0
        self.max_y = self.my
        self.max_z = 0
        self.frame = -1
        self.length = 0
        self.outlier_toggle = False
        self.average_toggle = False
        self.ratio = 1
        self.cop_x = np.zeros(15)
        self.cop_y = np.zeros(15)
        self.data = np.zeros((self.mx, self.my))

        self.line_pen = QtGui.QPen(QtCore.Qt.white)
        self.line_pen.setWidth(2)

        self.dot_pen = QtGui.QPen(QtCore.Qt.black)
        self.dot_pen.setWidth(2)
        self.dot_brush = QtGui.QBrush(QtCore.Qt.white)

        self.cop_lines = []
        self.cop_ellipses = []

        self.scene = QtGui.QGraphicsScene(self)
        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.image = QtGui.QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.main_layout = QtGui.QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.view)
        height = self.settings.contacts_widget_height()
        self.setMinimumHeight(height)
        self.setLayout(self.main_layout)

        pub.subscribe(self.clear_cached_values, "clear_cached_values")
        pub.subscribe(self.filter_outliers, "filter_outliers")
        pub.subscribe(self.update_average, "update_average")
        pub.subscribe(self.update_contact, "put_contact")
        pub.subscribe(self.show_average_results, "show_average_results")

    def show_average_results(self, toggle):
        self.average_toggle = toggle
        if self.parent.active:
            self.change_frame(frame=-1)

    def update_average(self):
        if self.contact_label in self.model.average_data:
            if self.parent.active:
                self.change_frame(frame=-1)

    def update_contact(self):
        if self.contact_label == self.model.contact.contact_label:
            if self.parent.active:
                self.change_frame(frame=-1)

    def filter_outliers(self, toggle):
        self.outlier_toggle = toggle
        if self.parent.active:
            self.change_frame(frame=-1)

    def get_data(self):
        if self.average_toggle:
            if self.frame == -1:
                self.data = self.model.average_data[self.contact_label].max(axis=2)
            else:
                self.data = self.model.average_data[self.contact_label][:, :, self.frame]
            self.length = self.model.average_data[self.contact_label].shape[2]
        else:
            if self.frame == -1:
                self.data = self.model.selected_contacts[self.contact_label].data.max(axis=2)
            else:
                self.data = self.model.selected_contacts[self.contact_label].data[:, :, self.frame]

            # Add padding, just like the average has
            self.data = np.pad(self.data, 2, mode="constant", constant_values=0)
            self.length = self.model.selected_contacts[self.contact_label].data.shape[2]

    def draw_cop(self):
        # If we still have the default shape, don't bother
        if self.data.shape == (1, 1):
            return

        # Remove all the previous ellipses if coming back from update_cop
        for item in self.cop_ellipses:
            self.scene.removeItem(item)
        self.cop_ellipses = []

        # This value determines how many points of the COP are being plotted.
        self.x = 15

        if self.average_toggle:
            data = self.model.average_data[self.contact_label]
        else:
            data = self.model.selected_contacts[self.contact_label].data
            data = np.pad(data, pad_width=((2,2),(2,2),(0,0)), mode="constant", constant_values=0)

        x, y, z = np.nonzero(data)
        # Just calculate the COP over the average measurement_data
        data = np.rot90(np.rot90(data))
        # For some reason I can't do the slicing in the above call
        data = data[:,::-1,:]

        # Only calculate the COP until we still have data in the frame
        self.cop_x, self.cop_y = calculations.calculate_cop(data[:,:, :np.max(z)])

        # Create a strided index
        z = data.shape[2]
        index = [x for x in xrange(0, z, int(z / self.x))]

        for frame in xrange(len(self.cop_x)-1):
            x1 = self.cop_x[frame]
            x2 = self.cop_x[frame + 1]
            y1 = self.cop_y[frame]
            y2 = self.cop_y[frame + 1]

            line = QtCore.QLineF(QtCore.QPointF(x1 * self.degree, y1 * self.degree),
                                 QtCore.QPointF(x2 * self.degree, y2 * self.degree))

            line = self.scene.addLine(line, self.line_pen)
            line.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
            self.cop_lines.append(line)

            # We only plot a couple of the ellipses
            if frame in index:
                ellipse = self.scene.addEllipse(x1 * self.degree, y1 * self.degree, 5, 5, self.dot_pen, self.dot_brush)
                ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
                self.cop_ellipses.append(ellipse)

        # Get the very last value
        x1, y1 = self.cop_x[-1], self.cop_y[-1]
        ellipse = self.scene.addEllipse(x1 * self.degree, y1 * self.degree, 5, 5, self.dot_pen, self.dot_brush)
        ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
        self.cop_ellipses.append(ellipse)

    def update_cop(self):
        # Remove all the previous ellipses
        for item in self.cop_ellipses:
            self.scene.removeItem(item)
        self.cop_ellipses = []
        # Only draw if the frame is actually available
        if self.frame < self.cop_x.shape[0]:
            cop_x = self.cop_x[self.frame]
            cop_y = self.cop_y[self.frame]
            ellipse = self.scene.addEllipse(cop_x * self.degree, cop_y * self.degree, 5, 5, self.dot_pen, self.dot_brush)
            ellipse.setTransform(QtGui.QTransform.fromScale(self.ratio, self.ratio), True)
            self.cop_ellipses.append(ellipse)

    def draw(self):
        if self.frame > self.length:
            return

        self.get_data()
        if self.frame == -1:
            self.draw_cop()
        else:
            self.update_cop()

        # Make sure the contacts are facing upright
        self.data = np.rot90(np.rot90(self.data))
        self.data = self.data[:, ::-1]
        # Display the average measurement_data for the requested frame
        self.pixmap = utility.get_qpixmap(self.data, self.degree, self.model.n_max, self.color_table)
        self.image.setPixmap(self.pixmap)
        self.resizeEvent()

    def change_frame(self, frame):
        self.frame = frame
        # See that we stay within bounds
        if (self.frame < self.length and
                    self.contact_label in self.model.average_data and
                    self.contact_label in self.model.selected_contacts):
            self.draw()

    def clear_cached_values(self):
        self.frame = -1
        self.data = np.zeros((self.mx, self.my))
        # Put the screen to black
        self.image.setPixmap(
            utility.get_qpixmap(np.zeros((self.mx, self.my)), self.degree, self.model.n_max, self.color_table))
        for point in self.cop_ellipses:
            self.scene.removeItem(point)
        self.cop_ellipses = []

        for cop in self.cop_lines:
            self.scene.removeItem(cop)
        self.cop_lines = []

    def resizeEvent(self, event=None):
        item_size = self.view.mapFromScene(self.image.sceneBoundingRect()).boundingRect().size()
        ratio = min(self.view.viewport().width() / float(item_size.width()),
                    self.view.viewport().height() / float(item_size.height()))

        if abs(1 - ratio) > 0.1:
            self.ratio = self.ratio * ratio
            self.image.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            for item in self.cop_ellipses:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            for item in self.cop_lines:
                item.setTransform(QtGui.QTransform.fromScale(ratio, ratio), True)
            self.view.setSceneRect(self.view.rect())
            self.view.centerOn(self.image)

