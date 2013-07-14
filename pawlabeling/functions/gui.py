#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PySide.QtGui import *
from PySide.QtCore import *

class Toolbar(QToolBar):
    def __init__(self, parent=None):
        super(Toolbar, self).__init__(parent)
        # I don't want to see it floating
        self.setFloatable(False)
        # I don't want it moved
        self.setMovable(False)
        # I want nice and big icons
        self.setIconSize(QSize(50, 50))

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