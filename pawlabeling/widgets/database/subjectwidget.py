import logging
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from pubsub import pub
from ...functions import io, gui
from ...settings import settings
from ...models import model
from ...functions import gui
from ..treewidgetitem import TreeWidgetItem


class SubjectWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SubjectWidget, self).__init__(parent)

        self.model = model.model
        label_font = settings.settings.label_font()
        date_format = settings.settings.date_format()

        self.subject_tree_label = QtGui.QLabel("Subjects")
        self.subject_tree_label.setFont(label_font)
        self.subject_tree = QtGui.QTreeWidget(self)
        #self.subject_tree.setMinimumWidth(300)
        #self.subject_tree.setMaximumWidth(400)
        self.subject_tree.setColumnCount(3)
        self.subject_tree.setHeaderLabels(["First Name", "Last Name", "Mass"])
        self.subject_tree.itemActivated.connect(self.put_subject)
        self.subject_tree.setSortingEnabled(True)

        self.subject_label = QtGui.QLabel("Subject")
        self.subject_label.setFont(label_font)
        self.birthday_label = QtGui.QLabel("Birthday")
        self.mass_label = QtGui.QLabel("Mass")
        self.first_name_label = QtGui.QLabel("First Name")
        self.last_name_label = QtGui.QLabel("Last Name")
        self.address_label = QtGui.QLabel("Address")
        self.city_label = QtGui.QLabel("City")
        self.phone_label = QtGui.QLabel("Phone")
        self.email_label = QtGui.QLabel("Email")

        self.birthday = QtGui.QDateTimeEdit(QtCore.QDate.currentDate())
        self.birthday.setMinimumDate(QtCore.QDate.currentDate().addYears(-100))
        self.birthday.setMaximumDate(QtCore.QDate.currentDate())
        self.birthday.setDisplayFormat(date_format)
        self.mass = QtGui.QLineEdit()
        self.first_name = QtGui.QLineEdit()
        self.last_name = QtGui.QLineEdit()
        self.address = QtGui.QLineEdit()
        self.city = QtGui.QLineEdit()
        self.phone = QtGui.QLineEdit()
        self.email = QtGui.QLineEdit()

        self.subject_fields = ["birthday", "mass", "first_name", "last_name",
                               "address", "city", "phone", "email"]

        self.subject_layout = QtGui.QGridLayout()
        self.subject_layout.setSpacing(10)
        self.subject_layout.addWidget(self.first_name_label, 1, 0)
        self.subject_layout.addWidget(self.first_name, 1, 1)
        self.subject_layout.addWidget(self.last_name_label, 1, 2)
        self.subject_layout.addWidget(self.last_name, 1, 3)
        self.subject_layout.addWidget(self.address_label, 2, 0)
        self.subject_layout.addWidget(self.address, 2, 1)
        self.subject_layout.addWidget(self.city_label, 2, 2)
        self.subject_layout.addWidget(self.city, 2, 3)
        self.subject_layout.addWidget(self.phone_label, 3, 0)
        self.subject_layout.addWidget(self.phone, 3, 1)
        self.subject_layout.addWidget(self.email_label, 3, 2)
        self.subject_layout.addWidget(self.email, 3, 3)
        self.subject_layout.addWidget(self.mass_label, 4, 0)
        self.subject_layout.addWidget(self.mass, 4, 1)
        self.subject_layout.addWidget(self.birthday_label, 4, 2)
        self.subject_layout.addWidget(self.birthday, 4, 3)

        self.subject_tree_layout = QtGui.QVBoxLayout()
        self.subject_tree_layout.addWidget(self.subject_label)
        bar_1 = QtGui.QFrame(self)
        bar_1.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.subject_tree_layout.addWidget(bar_1)
        self.subject_tree_layout.addLayout(self.subject_layout)
        self.subject_tree_layout.addWidget(self.subject_tree_label)
        bar_2 = QtGui.QFrame(self)
        bar_2.setFrameShape(QtGui.QFrame.Shape.HLine)
        self.subject_tree_layout.addWidget(bar_2)
        self.subject_tree_layout.addWidget(self.subject_tree)

        self.setLayout(self.subject_tree_layout)

        pub.subscribe(self.update_subjects_tree, "get_subjects")

    def create_subject(self):
        subject = self.get_subject_fields()
        self.model.create_subject(subject=subject)
        self.model.get_subjects()

    def delete_subject(self):
        current_item = self.subject_tree.currentItem()
        subject_id = current_item.text(3)
        subject = self.model.subjects[subject_id]
        message = "Are you sure you want to delete subject: {} {}?".format(subject.first_name, subject.last_name)

        self.dialog = gui.Dialog(message=message, title="Delete subject?", parent=self)
        response = self.dialog.exec_()
        if response:
            self.model.delete_subject(subject=subject)


    def get_subject_fields(self):
        # TODO Check here if the required fields have been entered
        # Also add some validation, to check if they're acceptable
        subject = {}
        for field in self.subject_fields:
            if field == "birthday":
                date = getattr(self, field).date()
                if date == QtCore.QDate.currentDate():
                    subject[field] = ""
                else:
                    subject[field] = date.toString(Qt.ISODate)
            elif field == "mass":
                mass = getattr(self, field).text()
                if mass:
                    subject[field] = float(mass)
                else:
                    # If there's no mass, we'll use 1 (never divide by zero!)
                    subject[field] = 1.
            else:
                subject[field] = getattr(self, field).text()
        return subject

    def update_subjects_tree(self):
        # Clear any existing contacts
        self.subject_tree.clear()

        if not self.model.subjects.values():
            return

        # Add the subjects to the subject_tree
        for index, subject in enumerate(self.model.subjects.values()):
            rootItem = TreeWidgetItem(self.subject_tree)
            rootItem.setText(0, subject.first_name)
            rootItem.setText(1, subject.last_name)
            rootItem.setText(2, str(subject.mass))  # Note 1.0 is the default value, sorry!
            rootItem.setText(3, subject.subject_id)

        self.subject_tree.sortByColumn(0, Qt.AscendingOrder)
        # Select the first subject
        item = self.subject_tree.topLevelItem(0)
        self.subject_tree.setCurrentItem(item)
        self.put_subject()

    def put_subject(self, evt=None):
        current_item = self.subject_tree.currentItem()
        subject_id = current_item.text(3)
        subject = self.model.subjects[subject_id]
        self.model.put_subject(subject=subject)

    def get_subjects(self):
        self.model.get_subjects()

    def clear_subject_fields(self):
        for field in self.subject_fields:
            if field == "birthday":
                getattr(self, field).setDate(QtCore.QDate.currentDate())
            else:
                getattr(self, field).setText("")