from PySide import QtCore
from PySide.QtCore import Qt

from pubsub import pub

class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)
        self.parent = parent
        self._items = {}
        self._children = []

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._items[index.row()]
        elif role == Qt.EditRole:
            return self._items[index.row()]
        else:
            return None

    def setData(self, index, value, role = Qt.EditRole):
        if role == Qt.EditRole:
            self._items[index.row()] = str(value.toString().toUtf8())
            #pub.sendMessage("subject_changed")
            return True
        return False

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self._items[row])
        parentNode = parent.internalPointer()
        return self.createIndex(row, column, parentNode._children[row])

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        node = index.internalPointer()
        if node.parent is None:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(node.parent.row, 0, node.parent)

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def rowCount(self):
        return len(self._items)

    def columnCount(self):
        return len(self._items)

    def appendChild(self, items):
        self._children.append(TreeModel(items=items, parent=self))

    def child(self, row):
        return self._children[row]

    def childrenCount(self):
        return len(self._children)

    def hasChildren(self):
        if len(self._children) > 0:
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def removeRows(self, row, count, parent = Qt.QModelIndex()):
        if row < 0 or row > len(self._items):
            return

        self.beginRemoveRows(parent, row, row + count - 1)

        while count != 0:
            del self._items[row]
            count -= 1

        self.endRemoveRows()

    def addItem(self, item):
        self.beginInsertRows(Qt.QModelIndex(), len(self._items), len(self._items))
        self._items.append(str(item))
        self.endInsertRows()

    def reset(self):
        self._items = {}
        self._children = []