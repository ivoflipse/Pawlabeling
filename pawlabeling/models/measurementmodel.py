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
        measurement_name = measurement["measurement_name"]
        file_path = measurement["file_path"]

        self.measurement = measurement
        self.measurement["subject_id"] = self.subject_id
        self.measurement["session_id"] = self.session_id
        measurement_id = self.measurements_table.get_new_id()
        self.measurement["measurement_id"] = measurement_id

        if measurement_name[-3:] == "zip":
            # Store the file_name without the .zip
            self.measurement["measurement_name"] = measurement_name[:-4]

        result = self.measurements_table.get_measurement(measurement_name=self.measurement["measurement_name"])
        if result:
            return result["measurement_id"]

        # Check if the file is zipped or not and extract the raw measurement_data
        if measurement_name[-3:] == "zip":
            # Unzip the file
            input_file = io.open_zip_file(file_path)
        else:
            with open(file_path, "r") as infile:
                input_file = infile.read()

            # If the user wants us to zip it, zip it so they don't keep taking up so much space!
            if self.settings.zip_files():
                measurement_folder = self.settings.measurement_folder()
                io.zip_file(measurement_folder, measurement_name)

        # Get the plate info, so we can get the brand
        plate = plates[self.measurement["plate_id"]]

        # Extract the measurement_data
        self.measurement_data = io.load(input_file, brand=self.plate["brand"])
        number_of_rows, number_of_columns, number_of_frames = self.measurement_data.shape
        self.measurement["number_of_rows"] = number_of_rows
        self.measurement["number_of_columns"] = number_of_columns
        self.measurement["number_of_frames"] = number_of_frames
        self.measurement["orientation"] = io.check_orientation(self.measurement_data)
        self.measurement["maximum_value"] = self.measurement_data.max()  # Perhaps round this and store it as an int?

        # We're not going to store this, so we delete the key
        del self.measurement["file_path"]

        self.measurement_group = self.measurements_table.create_measurement(**self.measurement)
        return measurement_id

    def create_measurement_data(self, measurement_group, measurement, measurement_data):
        # Don't forget to store the measurement_data for the measurement as well!
        self.measurements_table.store_data(group=measurement_group,
                                           item_id=measurement["measurement_name"],
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