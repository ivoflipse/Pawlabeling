import logging
from pubsub import pub
from pawlabeling.models import tabelmodel

logger = logging.getLogger("logger")

# TODO make this globally accessible or something
class MissingIdentifier(Exception):
    pass

class SessionModel():
    def __init__(self):
        self.sessions_table = tabelmodel.SessionsTable()
        pub.subscribe(self.create_session, "create_session")

    def create_session(self, session=None):
        try:
            self.sessions_table.create_session(**session)
        except MissingIdentifier:
            logger.warning("SessionModel.create_session: Some of the required fields are missing")


