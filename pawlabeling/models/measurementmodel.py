import logging
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.functions import calculations, io
from pawlabeling.settings import settings


class MissingIdentifier(Exception):
    pass


class Measurements(object):
    def __init__(self, subject_id, session_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.measurements_table = table.MeasurementsTable(database_file=self.database_file,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)

    def create_measurement(self, measurement, plates):
        measurement_object = Measurement(subject_id=self.subject_id, session_id=self.session_id)

        # Be sure to strip the zip of if its there
        measurement_name = measurement["measurement_name"]
        if measurement_name[-3:] == "zip":
            measurement_name = measurement_name[:-4]
            # If it already exists, restore the Measurement object and return that
        result = self.measurements_table.get_measurement(measurement_name=measurement_name)
        if result:
            return

        measurement_id = self.measurements_table.get_new_id()
        # Else we create a copy of our own
        measurement_object.create_measurement(measurement_id=measurement_id,
                                              measurement=measurement,
                                              plates=plates)

        measurement = measurement_object.to_dict()
        # Finally we create the contact
        self.measurement_group = self.measurements_table.create_measurement(**measurement)
        return measurement_object

    def delete_measurement(self, measurement):
        # Delete both the row and the group
        self.measurements_table.remove_row(table=self.measurements_table.measurements_table,
                                       name_id="measurement_id",
                                       item_id=measurement.measurement_id)
        self.measurements_table.remove_group(where="/{}/{}".format(self.subject_id, self.session_id),
                                         name=measurement.measurement_id)

    def get_measurements(self):
        measurements = {}
        for measurement in self.measurements_table.get_measurements():
            measurement_object = Measurement(subject_id=self.subject_id,
                                             session_id=self.session_id)
            measurement_object.restore(measurement)
            measurements[measurement_object.measurement_id] = measurement_object
        return measurements

    def create_measurement_data(self, measurement, measurement_data):
        self.measurements_table.store_data(group=self.measurement_group,
                                           item_id=measurement.measurement_id,
                                           data=measurement_data)

    def get_measurement_data(self, measurement):
        group = self.measurements_table.get_group(self.measurements_table.session_group,
                                                  measurement.measurement_id)
        item_id = measurement.measurement_id
        measurement_data = self.measurements_table.get_data(group=group, item_id=item_id)
        return measurement_data

    def update_n_max(self):
        n_max = 0
        for measurement in self.measurements_table.measurements_table:
            max_value = measurement["maximum_value"]
            if max_value > n_max:
                n_max = max_value
        return n_max


class Measurement(object):
    def __init__(self, subject_id, session_id):
        self.subject_id = subject_id
        self.session_id = session_id

    def create_measurement(self, measurement_id, measurement, plates):
        # Get a new id for this measurement
        self.measurement_id = measurement_id
        file_path = measurement["file_path"]
        measurement_name = measurement["measurement_name"]

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
        self.plate_id = measurement["plate_id"]
        self.plate = plates[self.plate_id]

        self.date = measurement["date"]
        self.time = measurement["time"]

        # Extract the measurement_data
        self.measurement_data = io.load(input_file, brand=self.plate.brand)
        self.number_of_rows, self.number_of_columns, self.number_of_frames = self.measurement_data.shape
        self.orientation = io.check_orientation(self.measurement_data)
        self.maximum_value = self.measurement_data.max()  # Perhaps round this and store it as an int?
        self.frequency = measurement["frequency"]

    def load_file_path(self, measurement_name, file_path):
        # Check if the file is zipped or not and extract the raw measurement_data
        if self.zipped:
            # Unzip the file
            input_file = io.open_zip_file(file_path)
        else:
            with open(file_path, "r") as infile:
                input_file = infile.read()

            # If the user wants us to zip it, zip it so they don't keep taking up so much space!
            if settings.settings.zip_files():
                measurement_folder = settings.settings.measurement_folder()
                io.zip_file(measurement_folder, measurement_name)

        return input_file

    def restore(self, measurement):
        self.measurement_id = measurement["measurement_id"]
        self.session_id = measurement["session_id"]
        self.subject_id = measurement["subject_id"]
        self.plate_id = measurement["plate_id"]
        self.measurement_name = measurement["measurement_name"]
        self.number_of_frames = measurement["number_of_frames"]
        self.number_of_rows = measurement["number_of_rows"]
        self.number_of_columns = measurement["number_of_rows"]
        self.frequency = measurement["frequency"]
        self.orientation = measurement["orientation"]
        self.maximum_value = measurement["maximum_value"]
        self.date = measurement["date"]
        self.time = measurement["time"]
        # TODO Tag the data on here as well

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