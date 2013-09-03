import sys
import os
import logging
from PySide import QtGui, QtCore
from pubsub import pub
from pawlabeling.settings import configuration
from pawlabeling.functions.qsingleapplication import QtSingleApplication
from pawlabeling.models import model
from pawlabeling.widgets.analysis import analysiswidget
from pawlabeling.widgets.processing import processingwidget
from pawlabeling.widgets.database import databasewidget


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        # Set the screen dimensions, useful for when its not being run full screen
        self.setGeometry(configuration.main_window_size)
        # This will simply set the screen size to whatever is maximally possible,
        # while leaving the menubar + taskbar visible
        if not configuration.desktop:
            self.showMaximized()
        self.setWindowTitle(configuration.app_name)
        # Y U NO WORK?
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images\pawlabeling.png")))
        # Set up the logger before anything else
        self.logger = configuration.setup_logging()

        # Create the base model for the entire application
        # Make sure to do this first, in case anything relies on it
        self.model = model.Model()

        self.database_widget = databasewidget.DatabaseWidget(self)
        self.processing_widget = processingwidget.ProcessingWidget(self)
        self.analysis_widget = analysiswidget.AnalysisWidget(self)

        self.tab_dict = {0:"Database", 1:"Processing", 2:"Analysis"}

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self.tab_widget = QtGui.QTabWidget(self)
        self.tab_widget.addTab(self.database_widget, "Database")
        self.tab_widget.addTab(self.processing_widget, "Processing")
        self.tab_widget.addTab(self.analysis_widget, "Analysis")

        self.setCentralWidget(self.tab_widget)

        # Load all the measurements into the measurement tree
        #self.model.load_file_paths()
        # Then load the first measurement
        #self.processing_widget.load_first_file()

        self.installEventFilter(self)
        self.tab_widget.currentChanged.connect(self.change_tabs)
        pub.subscribe(self.change_status, "update_statusbar")

    def center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def change_tabs(self, event=None):
        current_index = self.tab_widget.currentIndex()
        pub.sendMessage("update_statusbar", status="Changing tabs to the {} tab".format(self.tab_dict[current_index]))
        if self.tab_widget.currentIndex() == 0:
            self.processing_widget.subscribe()
            pass  # Is there anything you'd like to run when you start the database_widget?
        elif self.tab_widget.currentIndex() == 1:
            self.processing_widget.subscribe()
            self.processing_widget.put_measurement()
        elif self.tab_widget.currentIndex() == 2:
            self.processing_widget.unsubscribe()
            self.analysis_widget.put_measurement()

    def change_status(self, status):
        self.logger.info(status)
        self.status.showMessage(status)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.matches(QtGui.QKeySequence.MoveToNextWord):
                self.processing_widget.entire_plate_widget.fast_forward()
                return True
            elif event.matches(QtGui.QKeySequence.MoveToPreviousWord):
                self.processing_widget.entire_plate_widget.fast_backward()
                return True
            elif event.key() == QtCore.Qt.Key_Left:
                self.processing_widget.entire_plate_widget.slide_to_left()
                return True
            elif event.key() == QtCore.Qt.Key_Right:
                self.processing_widget.entire_plate_widget.slide_to_right()
                return True
            else:
                return False
        else:
            return False

def main():
    appGuid = 'F3FF80BA-BA05-4277-8063-82A6DB9245A2'
    app = QtSingleApplication(appGuid, sys.argv)
    if app.isRunning():
        print "Please close all other instances of the application before restarting"
        sys.exit(0)

    app.setApplicationName(configuration.app_name)
    app.setFont(QtGui.QFont("Helvetica", pointSize=10))
    window = MainWindow()
    window.show()
    window.raise_()
    app.exec_()

    logger = logging.getLogger("logger")
    logger.info("Application Shutdown\n")

if __name__ == "__main__":
    main()










            
