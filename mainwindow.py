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
            checkable=False,
            connection=self.mainWidget.trackContacts
        )

        self.storeStatus = self.createAction(text="&Store",
            shortcut="CTRL+S", icon=QIcon(os.path.join(os.path.dirname(__file__), "images/save-icon.png")),
            tip="Mark the tracking as correct",
            checkable=False,
            connection=self.mainWidget.storeStatus
        )


        self.slideLeft = self.createAction(text="Slide Left",
            shortcut=Qt.Key_Left, icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-left-icon.png")),
            tip="Move the slider to the left",
            checkable=False,
            connection=self.mainWidget.slideToLeft
        )

        self.slideRight = self.createAction(text="Slide Right",
            shortcut=Qt.Key_Right, icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-right-icon.png")),
            tip="Move the slider to the right",
            checkable=False,
            connection=self.mainWidget.slideToRight
        )

        self.fastBackward = self.createAction(text="Fast Back",
            shortcut=QKeySequence(Qt.CTRL + Qt.Key_Left),
            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-left-icon.png")),
            tip="Move the slider to the left faster",
            checkable=False,
            connection=self.mainWidget.fastBackward
        )

        self.fastForward = self.createAction(text="Fast Left Right",
            shortcut=QKeySequence(Qt.CTRL + Qt.Key_Right),
            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/arrow-right-icon.png")),
            tip="Move the slider to the right faster",
            checkable=False,
            connection=self.mainWidget.fastForward
        )

        self.front_left = self.createAction(text="Select Left Front",
                                            shortcut=QKeySequence(Qt.Key_7),
                                            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/LF-icon.png")),
                                            tip="Select the Left Front paw",
                                            checkable=False,
                                            connection=self.mainWidget.select_left_front
        )

        self.hind_left = self.createAction(text="Select Left Hind",
                                            shortcut=QKeySequence(Qt.Key_1),
                                            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/LH-icon.png")),
                                            tip="Select the Left Hind paw",
                                            checkable=False,
                                            connection=self.mainWidget.select_left_hind
        )

        self.front_right = self.createAction(text="Select Right Front",
                                            shortcut=QKeySequence(Qt.Key_9),
                                            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/RF-icon.png")),
                                            tip="Select the Right Front paw",
                                            checkable=False,
                                            connection=self.mainWidget.select_right_front
        )

        self.hind_right = self.createAction(text="Select Right Hind",
                                            shortcut=QKeySequence(Qt.Key_3),
                                            icon=QIcon(os.path.join(os.path.dirname(__file__), "images/RH-icon.png")),
                                            tip="Select the Right Hind paw",
                                            checkable=False,
                                            connection=self.mainWidget.select_right_hind
        )

        self.previous_paw = self.createAction(text="Select Previous Paw",
                                              shortcut=[QKeySequence(Qt.Key_4), Qt.Key_Up],
                                              icon=QIcon(os.path.join(os.path.dirname(__file__), "images/backward.png")),
                                              tip="Select the previous paw",
                                              checkable=False,
                                              connection=self.mainWidget.previous_paw
        )

        self.next_paw = self.createAction(text="Select Next Paw",
                                              shortcut=QKeySequence(Qt.Key_6),
                                              icon=QIcon(os.path.join(os.path.dirname(__file__), "images/forward.png")),
                                              tip="Select the next paw",
                                              checkable=False,
                                              connection=self.mainWidget.next_paw
        )

        self.actions = [self.storeStatus, self.trackContacts, self.front_left, self.hind_left,
                        self.front_right, self.hind_right, self.previous_paw, self.next_paw]

        for action in self.actions:
            action.setShortcutContext(Qt.ApplicationShortcut)
            self.toolbar.addAction(action)

        # Not adding the forward/backward buttons to the toolbar
        self.non_toolbar_actions = [self.slideLeft, self.slideRight, self.fastBackward, self.fastForward]
        for action in self.non_toolbar_actions:
            action.setShortcutContext(Qt.ApplicationShortcut)

        # Install an event filter
        self.arrowFilter = utility.arrowFilter()
        self.installEventFilter(self.arrowFilter)

        self.mainWidget.loadFile(event=None)


    def createAction(self, text, shortcut=None, icon=None,
                     tip=None, checkable=False, connection=None):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(icon)
        if shortcut is not None:
            if type(shortcut) == list:
                for s in shortcut:
                    action.setShortcut(s)
            else:
                action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if checkable:
            action.setCheckable(True)
        if connection:
            action.triggered.connect(connection)
        return action


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(name)
    window.show()
    window.raise_()
    app.exec_()










            
