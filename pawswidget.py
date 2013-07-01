from PyQt4.QtCore import *
from PyQt4.QtGui import *

from matplotlib import use, rcParams
use('Qt4Agg')
rcParams['backend.qt4']='PyQt4'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy as np
import utility

class PawsWidget(QWidget):
    def __init__(self, parent, degree, nmax):
        super(PawsWidget, self).__init__(parent)
        self.parent = parent
        self.degree = degree

        self.left_front = PawWidget(self, degree, nmax)
        self.left_hind = PawWidget(self, degree, nmax)
        self.right_front = PawWidget(self, degree, nmax)
        self.right_hind = PawWidget(self, degree, nmax)
        self.current_paw = PawWidget(self, degree, nmax)

        self.paws_list = [self.left_front, self.left_hind,
                          self.right_front, self.right_hind,
                          self.current_paw]
        # This sets every widget to a zero image and initializes paws
        self.clear_paws()

        self.left_paws_layout = QVBoxLayout()
        self.left_paws_layout.addWidget(self.left_front)
        self.left_paws_layout.addWidget(self.left_hind)
        self.current_paw_layout = QVBoxLayout()
        self.current_paw_layout.addWidget(self.current_paw)
        self.right_paws_layout = QVBoxLayout()
        self.right_paws_layout.addWidget(self.right_front)
        self.right_paws_layout.addWidget(self.right_hind)

        self.mainLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.left_paws_layout)
        self.mainLayout.addLayout(self.current_paw_layout)
        self.mainLayout.addLayout(self.right_paws_layout)
        self.setLayout(self.mainLayout)

    def update_current_paw(self, data, paw_label, index):
        # Make sure that each paw is only mapped to exactly one paw
        self.paws[index] = (paw_label, data)
        data_list = []
        for index, item in self.paws.items():
            label, data = item
            if label == paw_label:
                data_list.append(data)
        widget = self.paws_list[paw_label]
        widget.update(data_list)

    def update_nmax(self, nmax):
        for paw in self.paws_list:
            paw.nmax = nmax

    def clear_paws(self):
        self.paws = {}
        for paw in self.paws_list:
            paw.clear_paws()


class PawWidget(QWidget):
    def __init__(self, parent, degree, nmax):
        super(PawWidget, self).__init__(parent)
        self.parent = parent
        self.degree = degree
        self.nmax = nmax
        self.imageCT = utility.ImageColorTable()
        self.color_table = self.imageCT.create_colortable()

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setGeometry(0, 0, 100, 100)
        self.image = QGraphicsPixmapItem()
        self.scene.addItem(self.image)

        self.max_pressure = QLabel(self)
        self.mean_duration = QLabel(self)
        self.mean_surface = QLabel(self)

        self.max_pressure.setText("{} N".format(0))
        self.mean_duration.setText("{} frames".format(0))
        self.mean_surface.setText("{} pixels".format(0))

        self.number_layout = QVBoxLayout()
        self.number_layout.addWidget(self.max_pressure)
        self.number_layout.addWidget(self.mean_duration)
        self.number_layout.addWidget(self.mean_surface)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.view)
        self.main_layout.addLayout(self.number_layout)
        self.setLayout(self.main_layout)

    def update(self, data_list):
        # Calculate an average paw from the list of arrays
        mean_data_list = []
        pressures = []
        surfaces = []
        durations = []
        for data in data_list:
            mean_data_list.append(data.max(axis=2))
            pressures.append(np.max(np.sum(np.sum(data, axis=0), axis=0)))
            x, y, z = data.shape
            durations.append(z)
            surfaces.append(np.max([np.count_nonzero(data[:,:,frame]) for frame in range(z)]))

        self.max_pressure.setText("{} N".format(int(np.max(pressures))))
        self.mean_duration.setText("{} frames".format(int(np.mean(durations))))
        self.mean_surface.setText("{} pixels".format(int(np.mean(surfaces))))

        data = utility.averagecontacts(mean_data_list)
        self.data = np.rot90(np.rot90(data))
        self.image.setPixmap(utility.getQPixmap(self.data, self.degree, self.nmax, self.color_table))

    def clear_paws(self):
        self.data = None
        # Put the screen to black
        self.image.setPixmap(utility.getQPixmap(np.zeros((20,20)), self.degree, self.nmax, self.color_table))