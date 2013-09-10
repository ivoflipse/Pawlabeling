import sys
import os
import logging
from PySide import QtGui, QtCore
from pubsub import pub
# Set this right away, so its set for the whole application
# http://stackoverflow.com/questions/6723527/getting-pyside-to-work-with-matplotlib
import matplotlib
matplotlib.use("Qt4Agg")
matplotlib.rcParams["backend.qt4"] ="PySide"

from pawlabeling.configuration import configuration
from pawlabeling.functions.qsingleapplication import QtSingleApplication
from pawlabeling.models import model
from pawlabeling.widgets.analysis import analysiswidget
from pawlabeling.widgets.processing import processingwidget
from pawlabeling.widgets.database import databasewidget
from pawlabeling.widgets.settings import settingswidget


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.configuration = configuration.Configuration()

        # Set the screen dimensions, useful for when its not being run full screen
        # self.setGeometry(configuration.main_window_size)
        # self.setGeometry(self.configuration.value("widgets/main_window_size"))
        # Apparently its better to do it like this
        width = self.configuration.value("widgets/main_window_width")
        height = self.configuration.value("widgets/main_window_height")
        self.resize(width, height)
        x = self.configuration.value("widgets/main_window_left")
        y = self.configuration.value("widgets/main_window_top")
        self.move(x, y)

        # This will simply set the screen size to whatever is maximally possible,
        # while leaving the menubar + taskbar visible
        if not self.configuration.value("application/show_maximized"):
            self.showMaximized()

        self.setObjectName("MainWindow")
        self.setWindowTitle(parent.applicationName())
        # Y U NO WORK?
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images\pawlabeling.png")))
        # Set up the logger before anything else
        self.logger = self.configuration.setup_logging()

        # Create the base model for the entire application
        # Make sure to do this first, in case anything relies on it
        self.model = model.Model()

        self.database_widget = databasewidget.DatabaseWidget(self)
        self.processing_widget = processingwidget.ProcessingWidget(self)
        self.analysis_widget = analysiswidget.AnalysisWidget(self)
        self.settings_widget = settingswidget.SettingsWidget(self)

        self.tab_dict = {0:"Database", 1:"Processing",
                         2:"Analysis", 3:"Settings"}

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self.message_box = QtGui.QMessageBox()

        self.tab_widget = QtGui.QTabWidget(self)
        self.tab_widget.addTab(self.database_widget, "Database")
        self.tab_widget.addTab(self.processing_widget, "Processing")
        self.tab_widget.addTab(self.analysis_widget, "Analysis")
        self.tab_widget.addTab(self.settings_widget, "Settings")
        self.tab_widget.currentChanged.connect(self.change_tabs)

        self.setCentralWidget(self.tab_widget)

        self.installEventFilter(self)
        pub.subscribe(self.change_status, "update_statusbar")
        pub.subscribe(self.launch_message_box, "message_box")

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
            #self.analysis_widget.calculate_results()  # I think this is already done
            self.analysis_widget.put_measurement()
        elif self.tab_widget.currentIndex() == 3:
            self.processing_widget.unsubscribe()

    def change_status(self, status):
        self.logger.info(status)
        self.status.showMessage(status)

    def launch_message_box(self, message):
        self.message_box.setText(message)
        self.message_box.exec_()

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

    def closeEvent(self, evt):
        # Write the current configurations to the configuration file
        if self.configuration.value("restore_last_session"):
            width, height = self.size()
            self.configuration.setValue("widgets/main_window_width", width)
            self.configuration.setValue("widgets/main_window_height", height)
            x, y = self.pos()
            self.configuration.setValue("widgets/main_window_left", x)
            self.configuration.setValue("widgets/main_window_top", y)

        self.logger = logging.getLogger("logger")
        self.logger.info("Application Shutdown\n")


def main():
    appGuid = 'F3FF80BA-BA05-4277-8063-82A6DB9245A2'
    app = QtSingleApplication(appGuid, sys.argv)
    if app.isRunning():
        print "Please close all other instances of the application before restarting"
        sys.exit(0)

    app.setOrganizationName("Flipse R&D")
    app.setOrganizationDomain("flipserd.com")
    app.setApplicationName("Paw Labeling")
    app.setFont(QtGui.QFont("Helvetica", pointSize=10))
    window = MainWindow(app)
    window.show()
    window.raise_()
    app.exec_()



if __name__ == "__main__":
    main()