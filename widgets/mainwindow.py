#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
import os

from PySide.QtCore import *
from PySide.QtGui import *
from settings import configuration
import processingwidget, analysiswidget


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        # This will simply set the screen size to whatever is maximally possible,
        # while leaving the menubar + taskbar visible
        self.showMaximized()
        self.setWindowTitle("Paw Labeling tool")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "images\\pawlabeling.png")))

        self.processing_widget = processingwidget.ProcessingWidget(self)
        self.analysis_widget = analysiswidget.AnalysisWidget(self)

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.processing_widget, "Processing")
        self.tab_widget.addTab(self.analysis_widget, "Analysis")

        self.setCentralWidget(self.tab_widget)

        # TODO call this function when you switch tabs
        # Load all the measurements into the measurement tree
        self.processing_widget.add_measurements()
        # Then load the first measurement
        self.processing_widget.load_first_file()

        self.installEventFilter(self)

        self.tab_widget.currentChanged.connect(self.change_tabs)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def change_tabs(self, event):
        # If the tab is the first tab, reload the measurements
        if self.tab_widget.currentIndex() == 0:
            self.processing_widget.add_measurements()
            self.processing_widget.load_first_file()
        if self.tab_widget.currentIndex() == 1:
            self.analysis_widget.add_measurements()
            self.analysis_widget.load_first_file()


    # TODO make sure that the tree does NOT do this
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.MoveToNextWord):
                self.processing_widget.entire_plate_widget.fast_forward()
                return True
            elif event.matches(QKeySequence.MoveToPreviousWord):
                self.processing_widget.entire_plate_widget.fast_backward()
                return True
            elif event.key() == Qt.Key_Left:
                self.processing_widget.entire_plate_widget.slide_to_left()
                return True
            elif event.key() == Qt.Key_Right:
                self.processing_widget.entire_plate_widget.slide_to_right()
                return True
        else:
            return False


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.raise_()
    app.exec_()


if __name__ == "__main__":
    main()










            
