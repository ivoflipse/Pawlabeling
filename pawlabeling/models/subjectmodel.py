import logging
from pubsub import pub
from pawlabeling.models import tabelmodel

logger = logging.getLogger("logger")

class MissingIdentifier(Exception):
    pass

class SubjectModel():
    def __init__(self):
        self.subjects_table = tabelmodel.SubjectsTable()
        pub.subscribe(self.create_subject, "create_subject")

    def create_subject(self, subject):
        """
        This function takes a subject dictionary object and stores it in PyTables
        """
        try:
            self.subjects_table.create_subject(**subject)
        except MissingIdentifier:
            logger.warning("SubjectModel.create_subject: Some of the required fields are missing")



