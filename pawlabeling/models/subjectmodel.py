import logging
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.settings import settings

class MissingIdentifier(Exception):
    pass

class SubjectModel(object):
    def __init__(self):
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.subjects_table = table.SubjectsTable(database_file=self.database_file)
        self.logger = logging.getLogger("logger")

    def create_subject(self, subject):
        """
        This function takes a subject dictionary object and stores it in PyTables
        """
        # TODO Add some other validation to see if the input values are correct
        # Check if the subject is already in the table
        if self.subjects_table.get_subject(plate=subject["first_name"], last_name=subject["last_name"],
                                           birthday=subject["birthday"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_subject: Subject already exists")
            return

        # Create a subject id
        subject_id = self.subjects_table.get_new_id()
        subject["subject_id"] = subject_id

        self.subject_group = self.subjects_table.create_subject(**subject)
        pub.sendMessage("update_statusbar", status="Model.create_subject: Subject created")


    def get_subjects(self, subject={}):
        self.subjects = self.subjects_table.get_subjects(**subject)
        pub.sendMessage("update_subjects_tree", subjects=self.subjects)


    def put_subject(self, subject):
        # Whenever we switch subjects, clear the cache
        self.clear_cached_values()

        self.subject = subject
        self.subject_id = subject["subject_id"]

        self.logger.info("Subject ID set to {}".format(self.subject_id))
        # As soon as a subject is selected, we instantiate our sessions table
        self.sessions_table = table.SessionsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id)
        pub.sendMessage("update_statusbar", status="Subject: {} {}".format(self.subject["first_name"],
                                                                           self.subject["last_name"]))
        self.get_sessions()