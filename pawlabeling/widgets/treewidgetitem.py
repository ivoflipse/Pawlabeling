from PySide import QtGui

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    """
    I want to sort based on the contact id as a number, not a string, so I am creating my own version
    based on this SO answer:
    http://stackoverflow.com/questions/21030719/sort-a-pyside-qtgui-qtreewidget-by-an-alpha-numeric-column
    """
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        key_1 = self.text(column)
        key_2 = other.text(column)

        # Use Ned Batchelder's human sort
        return alphanum_key(key_1) < alphanum_key(key_2)


# From: http://nedbatchelder.com/blog/200712/human_sorting.html
import re

def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]

def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)
