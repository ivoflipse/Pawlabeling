#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PySide.QtGui import *
from PySide.QtCore import *

class ArrowFilter(QObject):
    def eventFilter(self, parent, event=None):
        if event.type() == QEvent.KeyPress:
            # This seems to have some nasty consequences
            if event.matches(QKeySequence.MoveToNextWord):
                parent.fast_forward()
                return True
            elif event.matches(QKeySequence.MoveToPreviousWord):
                parent.fast_backward()
                return True
            elif event.key() == Qt.Key_Left:
                parent.slide_to_left()
                return True
            elif event.key() == Qt.Key_Right:
                parent.slide_to_right()
                return True
        return False

def create_action(parent=None, text="", shortcut=None, icon=None,
                  tip=None, checkable=False, connection=None):
    action = QAction(text, parent)
    if text:
        action.setText(text)
    if icon is not None:
        action.setIcon(icon)
    if shortcut is not None:
        if type(shortcut) == list:
            action.setShortcuts(shortcut)
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