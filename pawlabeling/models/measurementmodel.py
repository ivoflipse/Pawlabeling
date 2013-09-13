import logging
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.functions import calculations, io
from pawlabeling.settings import settings


class MissingIdentifier(Exception):
    pass


class MeasurementModel(object):
    def __init__(self, subject_id, session_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.measurements_table = table.MeasurementsTable(database_file=self.database_file,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)

    def create_measurement(self, measurement, plates):
        measurement_object = Measurement(subject_id=self.subject_id,
                                         session_id=self.session_id,
                                         measurement=measurement,
                                         plates=plates)

        measurement = measurement_object.to_dict()
        # Finally we create the contact
        self.measurement_group = self.measurements_table.create_measurement(**measurement)
        return measurement_object.measurement_id

    def create_measurement_data(self, measurement, measurement_data):
        # Don't forget to store the measurement_data for the measurement as well!
        self.measurements_table.store_data(group=self.measurement_group,
                                           item_id=measurement["measurement_id"],
                                           data=measurement_data)


    def get_measurements(self):
        measurements = self.measurements_table.get_measurements()
        return measurements

    def get_measurement_data(self, measurement):
        group = self.measurements_table.get_group(self.measurements_table.session_group,
                                                  measurement["measurement_id"])
        item_id = measurement["measurement_name"]
        measurement_data = self.measurements_table.get_data(group=group, item_id=item_id)
        return measurement_data

    def update_n_max(self):
        n_max = 0
        for m in self.measurements_table.measurements_table:
            nm = m["maximum_value"]
            if nm > n_max:
                n_max = nm
        return n_max


class Measurement(object):
    def __init__(self, subject_id, session_id, measurement, plates):
        self.subject_id = subject_id
        self.session_id = session_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.measurements_table = table.MeasurementsTable(database_file=self.database_file,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)

        # Get a new id for this measurement
        self.measurement_id = self.measurements_table.get_new_id()
        file_path = measurement["file_path"]
        measurement_name = measurement["measurement_name"]

        # Check if the measurement already exists, if so, return the measurement_id
        measurement = self.measurements_table.get_measurement(measurement_name=measurement_name)
        if measurement:
            self.restore(measurement)

        # Strip the .zip from the measurement_name
        if measurement_name[-3:] == "zip":
            self.zipped = True
            self.measurement_name = measurement_name[:-4]
        else:
            self.zipped = False
            self.measurement_name = measurement_name

        # Get the raw string from the file path
        input_file = self.load_file_path(measurement_name, file_path=file_path)

        # Get the plate info, so we can get the brand
        plate = plates[measurement["plate_id"]]

        # Extract the measurement_data
        self.measurement_data = io.load(input_file, brand=plate["brand"])
        self.number_of_rows, self.number_of_columns, self.number_of_frames = self.measurement_data.shape
        self.orientation = io.check_orientation(self.measurement_data)
        self.maximum_value = self.measurement_data.max()  # Perhaps round this and store it as an int?
        self.frequency = measurement["frequency"]

        # Finally we create the contact
        self.measurement_group = self.measurements_table.create_measurement(**measurement)

    def load_file_path(self, measurement_name, file_path):
        # Check if the file is zipped or not and extract the raw measurement_data
        if self.zipped:
            # Unzip the file
            input_file = io.open_zip_file(file_path)
        else:
            with open(file_path, "r") as infile:
                input_file = infile.read()

            # If the user wants us to zip it, zip it so they don't keep taking up so much space!
            if self.settings.zip_files():
                measurement_folder = self.settings.measurement_folder()
                io.zip_file(measurement_folder, measurement_name)

        return input_file


    def restore(self, measurement):
        self.measurement_id = measurement["measurement_id"]
        self.session_id = measurement["session_id"]
        self.subject_id = measurement["subject_id"]
        self.plate_id = measurement["plate_id"]
        self.measurement_name = measurement["measurement_name"]
        self.number_of_frames = measurement["number_of_frames"]
        self.number_of_rows = measurement[""]
        self.number_of_columns = measurement["number_of_rows"]
        self.frequency = measurement["frequency"]
        self.orientation = measurement["orientation"]
        self.maximum_value = measurement["maximum_value"]
        self.date = measurement["date"]
        self.time = measurement["time"]

    def to_dict(self):
        return {
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "measurement_id": self.measurement_id,
            "plate_id": self.plate_id,
            "measurement_name": self.measurement_name,
            "number_of_frames": self.number_of_frames,
            "number_of_rows": self.number_of_rows,
            "number_of_columns": self.number_of_columns,
            "frequency": self.frequency,
            "orientation": self.orientation,
            "maximum_value": self.maximum_value,
            "date": self.date,
            "time": self.time
        }