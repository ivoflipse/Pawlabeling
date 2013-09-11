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
        self.logger = logging.getLogger("logger")
        pub.subscribe(self.create_measurement, "create_measurement")

    # TODO consider moving this to a Measurement class or at least refactoring it
    def create_measurement(self, measurement):
        if not self.session_id:
            pub.sendMessage("update_statusbar", status="Model.create_measurement: Session not selected")
            pub.sendMessage("message_box", message="Please select a session")
            return

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

        if self.measurements_table.get_measurement_row(measurement_name=self.measurement["measurement_name"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement already exists")
            return

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
        plate = self.plates[self.measurement["plate_id"]]
        self.put_plate(plate)

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
        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement created")
        # Don't forget to store the measurement_data for the measurement as well!
        self.measurements_table.store_data(group=self.measurement_group,
                                           item_id=self.measurement["measurement_name"],
                                           data=self.measurement_data)
        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement data created")

        self.contacts_table = table.ContactsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=measurement_id)
        contacts = self.track_contacts()
        for contact in contacts:
            contact = contact.to_dict()  # This takes care of some of the book keeping for us
            contact["subject_id"] = self.subject_id
            contact["session_id"] = self.session_id
            contact["measurement_id"] = self.measurement["measurement_id"]
            self.create_contact(contact)


    def get_measurements(self, measurement={}):
        self.measurements = self.measurements_table.get_measurements(**measurement)
        pub.sendMessage("update_measurements_tree", measurements=self.measurements)
        # From one of the measurements, get its plate_id and call put_plate
        if self.measurements:
            # Update the plate information
            plate = self.plates[self.measurements[0]["plate_id"]]
            self.put_plate(plate)


    def put_measurement(self, measurement):
        for m in self.measurements:
            if m["measurement_name"] == measurement["measurement_name"]:
                measurement = m

        self.measurement = measurement
        self.measurement_id = measurement["measurement_id"]
        self.measurement_name = measurement["measurement_name"]
        self.logger.info("Measurement ID set to {}".format(self.measurement_id))
        self.contacts_table = table.ContactsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)
        pub.sendMessage("update_statusbar", status="Measurement: {}".format(self.measurement_name))
        pub.sendMessage("update_measurement", measurement=self.measurement)

    def get_measurement_data(self):
        group = self.measurements_table.get_group(self.measurements_table.session_group,
                                                  self.measurement["measurement_id"])
        item_id = self.measurement_name
        self.measurement_data = self.measurements_table.get_data(group=group, item_id=item_id)
        pub.sendMessage("update_measurement_data", measurement_data=self.measurement_data)

    def update_n_max(self):
        self.n_max = 0
        for m in self.measurements_table.measurements_table:
            n_max = m["maximum_value"]
            if n_max > self.n_max:
                self.n_max = n_max
        pub.sendMessage("update_n_max", n_max=self.n_max)