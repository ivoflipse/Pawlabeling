from PySide import QtGui, QtCore

class Toolbar(QtGui.QToolBar):
    def __init__(self, parent=None):
        super(Toolbar, self).__init__(parent)
        # I don't want to see it floating
        self.setFloatable(False)
        # I don't want it moved
        self.setMovable(False)
        # I want nice and big icons
        self.setIconSize(QtCore.QSize(50, 50))

def create_action(parent=None, text="", shortcut=None, icon=None,
                  tip=None, checkable=False, connection=None):
    action = QtGui.QAction(text, parent)
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