import logging
from pawlabeling.models import table
from pawlabeling.settings import settings


class MissingIdentifier(Exception):
    pass


class Subjects(object):
    def __init__(self):
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.subjects_table = table.SubjectsTable(database_file=self.database_file)
        self.logger = logging.getLogger("logger")

    def create_subject(self, subject):
        """
        This function takes a subject dictionary object and stores it in PyTables
        """
        subject_object = Subject()
        # TODO Add some other validation to see if the input values are correct
        # Check if the subject is already in the table
        if self.subjects_table.get_subject(plate=subject["first_name"],
                                           last_name=subject["last_name"],
                                           birthday=subject["birthday"]):
            return

        subject_id = self.subjects_table.get_new_id()
        subject_object.create_subject(subject_id=subject_id, subject=subject)
        subject = subject_object.to_dict()
        # Create a new subject
        self.subject_group = self.subjects_table.create_subject(**subject)
        return subject_object

    def delete_subject(self, subject):
        # Delete both the row and the group
        self.subjects_table.remove_row(table=self.subjects_table.subjects_table,
                                       name_id="subject_id",
                                       item_id=subject.subject_id)
        self.subjects_table.remove_group(where="/", name=subject.subject_id)

    def get_subjects(self):
        subjects = {}
        for subject in self.subjects_table.get_subjects():
            subject_object = Subject()
            subject_object.restore(subject)
            subjects[subject_object.subject_id] = subject_object
        return subjects


class Subject(object):
    """
        subject_id = tables.StringCol(64)
        first_name = tables.StringCol(32)
        last_name = tables.StringCol(32)
        address = tables.StringCol(32)
        city = tables.StringCol(32)
        phone = tables.StringCol(32)
        email = tables.StringCol(32)
        birthday = tables.StringCol(32)
        mass = tables.FloatCol()
    """

    def __init__(self):
        pass

    def create_subject(self, subject_id, subject):
        self.subject_id = subject_id
        self.first_name = subject["first_name"]
        self.last_name = subject["last_name"]
        self.address = subject["address"]
        self.city = subject["city"]
        self.phone = subject["phone"]
        self.email = subject["email"]
        self.birthday = subject["birthday"]
        self.mass = subject["mass"]

    def to_dict(self):
        subject = {
            "subject_id": self.subject_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "address": self.address,
            "city": self.city,
            "phone": self.phone,
            "email": self.email,
            "birthday": self.birthday,
            "mass": self.mass
        }
        return subject

    def restore(self, subject):
        self.subject_id = subject["subject_id"]
        self.first_name = subject["first_name"]
        self.last_name = subject["last_name"]
        self.address = subject["address"]
        self.city = subject["city"]
        self.phone = subject["phone"]
        self.email = subject["email"]
        self.birthday = subject["birthday"]
        self.mass = subject["mass"]
