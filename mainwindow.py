import sys, os

from mainwidget import MainWidget
from toolbar import Toolbar
import utility
from PyQt4.QtCore import *
from PyQt4.QtGui import *

base_folder = "C:\Dropbox\Public\Examples\\"
name = base_folder + "der_1 - 3-4-2010 - Entire Plate Roll Off"


class MainWindow(QMainWindow):
    def __init__(self, filename, parent=None):
        super(MainWindow, self).__init__(parent)
        desktop = True
        if desktop:
            # Set the size to something nice and large
            self.setGeometry(QRect(0, 25, 2250, 1000))
        else:
            self.setGeometry(QRect(0, 25, 1400, 800))

        path = "C:\\Exports\\"
        pickled = "C:\\LabelsPickled\\"
        # Add the folder for the pickled data if it doesn't exist
        if not os.path.exists(pickled):
            os.mkdir(pickled)

        self.mainWidget = MainWidget(path, pickled, desktop, self)
        self.setCentralWidget(self.mainWidget)
        self.toolbar = Toolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.status = self.statusBar()
        self.status.showMessage("Ready")
        self.setWindowTitle("Paw labeling tool")

        self.trackContacts = self.createAction(text="&Track Contacts",
            shortcut="CTRL+F", icon=QIcon(os.path.join(os.path.dirname(__file__), "images/editzoom.png")),
            tip="Using the tracker to find contacts",
            checkable=False        )

        self.goodResult = self.createAction(text="&Store",
            shortcut="CTRL+S", icon=QIcon(os.path.join(os.path.dirname(__file__), "images/save-icon.png")),
            tip="Mark the tracking as correct",
            checkable=False        )


        self.slideLeft = self.createAction(text="Slide Left",
            shortcut=Qt.Key_Left, icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-left-icon.png")),
            tip="Move the slider to the left",
            checkable=False        )

        self.slideRight = self.createAction(text="Slide Right",
            shortcut=Qt.Key_Right, icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-right-icon.png")),
            tip="Move the slider to the right",
            checkable=False        )

        self.fastBackward = self.createAction(text="Fast Back",
            shortcut=QKeySequence(Qt.CTRL + Qt.Key_Left),
            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-left-icon.png")),
            tip="Move the slider to the left faster",
            checkable=False        )

        self.fastForward = self.createAction(text="Fast Left Right",
            shortcut=QKeySequence(Qt.CTRL + Qt.Key_Right),
            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-right-icon.png")),
            tip="Move the slider to the right faster",
            checkable=False        )

        self.goodResult.setShortcutContext(Qt.ApplicationShortcut)
        self.trackContacts.setShortcutContext(Qt.ApplicationShortcut)
        self.slideLeft.setShortcutContext(Qt.ApplicationShortcut)
        self.slideRight.setShortcutContext(Qt.ApplicationShortcut)
        self.fastBackward.setShortcutContext(Qt.ApplicationShortcut)
        self.fastForward.setShortcutContext(Qt.ApplicationShortcut)

        self.toolbar.addAction(self.trackContacts)
        self.toolbar.addAction(self.storeStatus)
        self.toolbar.addAction(self.slideLeft)
        self.toolbar.addAction(self.slideRight)
        self.toolbar.addAction(self.fastBackward)
        self.toolbar.addAction(self.fastForward)

        self.trackContacts.triggered.connect(self.mainWidget.trackContacts)
        self.goodResult.triggered.connect(self.mainWidget.goodResult)
        self.slideLeft.triggered.connect(self.mainWidget.slideToLeft)
        self.slideRight.triggered.connect(self.mainWidget.slideToRight)
        self.fastBackward.triggered.connect(self.mainWidget.fastBackward)
        self.fastForward.triggered.connect(self.mainWidget.fastForward)

        # Install an event filter
        self.arrowFilter = utility.arrowFilter()
        self.installEventFilter(self.arrowFilter)

        self.mainWidget.setFileName(event=None)


    def createAction(self, text, shortcut=None, icon=None,
                     tip=None, checkable=False, connection=None):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(icon)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if checkable:
            action.setCheckable(True)
        return action


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(name)
    window.show()
    window.raise_()
    app.exec_()










            
