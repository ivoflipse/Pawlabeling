import logging
from pubsub import pub
from pawlabeling.models import table



# TODO make this globally accessible or something
class MissingIdentifier(Exception):
    pass

class SessionModel():
    def __init__(self):
        self.sessions_table = table.SessionsTable()
        self.logger = logging.getLogger("logger")
        pub.subscribe(self.create_session, "create_session")

    def create_session(self, session=None):
        try:
            self.sessions_table.create_session(**session)
        except MissingIdentifier:
            self.logger.warning("SessionModel.create_session: Some of the required fields are missing")


