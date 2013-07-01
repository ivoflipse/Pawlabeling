from PyQt4.QtCore import *
from PyQt4.QtGui import *

class Toolbar(QToolBar):
    def __init__(self, parent = None):
        super(Toolbar, self).__init__(parent)
        # I don't want to see it floating
        self.setFloatable(False)
        # I don't want it moved
        self.setMovable(False)
        # I want nice and big icons
        self.setIconSize(QSize(50, 50))
