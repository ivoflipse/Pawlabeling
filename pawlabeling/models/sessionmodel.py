import logging
from pubsub import pub
from pawlabeling.models import tabelmodel



# TODO make this globally accessible or something
class MissingIdentifier(Exception):
    pass

class SessionModel():
    def __init__(self):
        self.sessions_table = tabelmodel.SessionsTable()
        self.logger = logging.getLogger("logger")
        pub.subscribe(self.create_session, "create_session")

    def set_parent_id(self, subject_id):
        self.sessions_table.set_parent_id(subject_id=subject_id)

    def create_session(self, session=None):
        try:
            self.sessions_table.create_session(**session)
        except MissingIdentifier:
            self.logger.warning("SessionModel.create_session: Some of the required fields are missing")


