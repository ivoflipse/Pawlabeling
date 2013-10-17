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

from ..settings import settings
from ..functions.qsingleapplication import QtSingleApplication
from ..models import model
from ..widgets.analysis import analysiswidget
from ..widgets.processing import processingwidget
from ..widgets.database import databasewidget
from ..widgets.settings import settingswidget


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.settings = settings.settings
        # Set up the logger before anything else
        self.logger = self.settings.logger
        # Set the screen dimensions, useful for when its not being run full screen
        # self.setGeometry(settings.main_window_size)
        # self.setGeometry(self.settings.value("widgets/main_window_size"))
        # Apparently its better to do it like this
        width = self.settings.main_window_width()
        height = self.settings.main_window_height()
        self.resize(width, height)
        x = self.settings.main_window_left()
        y = self.settings.main_window_top()
        self.move(x, y)

        # This will simply set the screen size to whatever is maximally possible,
        # while leaving the menubar + taskbar visible
        if self.settings.show_maximized():
            self.showMaximized()

        self.setObjectName("MainWindow")
        self.setWindowTitle(parent.applicationName())
        # Y U NO WORK?
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images\pawlabeling.png")))

        # Create the base model for the entire application
        # Make sure to do this first, in case anything relies on it
        self.model = model.model

        self.database_widget = databasewidget.DatabaseWidget(self)
        self.processing_widget = processingwidget.ProcessingWidget(self)
        self.analysis_widget = analysiswidget.AnalysisWidget(self)
        self.settings_widget = settingswidget.SettingsWidget(self)

        self.tab_dict = {0:"Database", 1:"Processing",
                         2:"Analysis", 3:"Settings"}

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self.progress = QtGui.QProgressBar()
        self.progress.setRange(0, 100)
        self.status.addPermanentWidget(self.progress)

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
        pub.subscribe(self.update_progress, "update_progress")
        pub.subscribe(self.launch_message_box, "message_box")
        pub.subscribe(self.changed_settings, "changed_settings")

        # This has to be called after all widgets have been created
        self.model.get_subjects()

    def center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def change_tabs(self, event=None):
        current_index = self.tab_widget.currentIndex()
        pub.sendMessage("update_statusbar", status="Changing tabs to the {} tab".format(self.tab_dict[current_index]))
        if self.tab_widget.currentIndex() == 0:
            pass
        elif self.tab_widget.currentIndex() == 1:
            self.processing_widget.measurement_tree.select_initial_measurement()
        elif self.tab_widget.currentIndex() == 2:
            self.analysis_widget.measurement_tree.select_initial_measurement()
            # Calculate the results if it hasn't been done already
            self.model.calculate_results()
        elif self.tab_widget.currentIndex() == 3:
            self.processing_widget.unsubscribe()
            self.settings_widget.update_fields()

    def changed_settings(self):
        width = self.settings.main_window_width()
        height = self.settings.main_window_height()
        self.resize(width, height)
        x = self.settings.main_window_left()
        y = self.settings.main_window_top()
        self.move(x, y)

    def change_status(self, status):
        self.logger.info(status)
        self.status.showMessage(status)

    def update_progress(self, progress):
        """
        If we start displaying progress, create a progress bar.
        Once we reach 100%, remove it again
        """
        if progress == 0:
            self.progress.reset()
        else:
            self.progress.setValue(progress)

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

    def closeEvent(self, event):
        # Write the current configurations to the settings file
        if self.settings.restore_last_session():
            size = self.size()
            pos = self.pos()
            self.settings.write_value("widgets/main_window_width", size.width())
            self.settings.write_value("widgets/main_window_height", size.height())
            self.settings.write_value("widgets/main_window_left", pos.x())
            self.settings.write_value("widgets/main_window_top", pos.y())

        self.logger = logging.getLogger("logger")
        self.logger.info("Application Shutdown\n")

        event.accept()

def main():
    appGuid = 'F3FF80BA-BA05-4277-8063-82A6DB9245A2'
    app = QtSingleApplication(appGuid, sys.argv)
    if app.isRunning():
        print "Please close all other instances of the application before restarting"
        sys.exit(0)

    app.setFont(QtGui.QFont("Helvetica", pointSize=10))
    window = MainWindow(app)
    window.show()
    window.raise_()
    app.exec_()



if __name__ == "__main__":
    main()