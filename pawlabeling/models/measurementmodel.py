import logging
from pubsub import pub
from pawlabeling.models import tabelmodel


class MissingIdentifier(Exception):
    pass


class MeasurementModel():
    def __init__(self):
        self.measurements_table = tabelmodel.MeasurementsTable()
        self.logger = logging.getLogger("logger")
        pub.subscribe(self.create_measurement, "create_measurement")

    def set_parent_id(self, subject_id, session_id):
        self.measurements_table.set_parent_id(subject_id=subject_id, session_id=session_id)

    def create_measurement(self, measurement=None):
        try:
            self.measurements_table.create_measurement(**measurement)
        except MissingIdentifier:
            self.logger.warning("MeasurementModel.create_measurement: Some of the required fields are missing")


