from collections import defaultdict
import logging
import os
import numpy as np
from pubsub import pub
from pawlabeling.functions import utility, io, tracking, calculations
from pawlabeling.settings import settings
from pawlabeling.models import contactmodel, table
#from memory_profiler import profile


class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.settings = settings.settings
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()

        self.subjects_table = table.SubjectsTable(database_file=self.database_file)
        self.plates_table = table.PlatesTable(database_file=self.database_file)
        plates = self.settings.setup_plates()
        # If not all plates are in the plates table, add them
        if len(self.plates_table.plates_table) != len(plates):
            for plate in plates:
                self.create_plate(plate)

        # Keep a dictionary with all the plates with their id as the key
        self.plates = {}
        for plate in self.plates_table.get_plates(plate={}):
            self.plates[plate["plate_id"]] = plate

        self.subject_name = ""
        self.measurement_name = ""
        self.session_id = ""
        self.subject_id = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()

        self.logger = logging.getLogger("logger")

        # OLD
        pub.subscribe(self.load_contacts, "load_contacts")
        pub.subscribe(self.update_current_contact, "update_current_contact")
        pub.subscribe(self.store_contacts, "store_contacts")
        pub.subscribe(self.repeat_track_contacts, "track_contacts")
        pub.subscribe(self.calculate_results, "calculate_results")
        # CREATE
        pub.subscribe(self.create_subject, "create_subject")
        pub.subscribe(self.create_session, "create_session")
        pub.subscribe(self.create_measurement, "create_measurement")
        pub.subscribe(self.create_contact, "create_contact")
        pub.subscribe(self.create_plate, "create_plate")
        # GET
        pub.subscribe(self.get_subjects, "get_subjects")
        pub.subscribe(self.get_sessions, "get_sessions")
        pub.subscribe(self.get_measurements, "get_measurements")
        pub.subscribe(self.get_contacts, "get_contacts")
        pub.subscribe(self.get_measurement_data, "get_measurement_data")
        pub.subscribe(self.get_plates, "get_plates")
        # PUT
        pub.subscribe(self.put_subject, "put_subject")
        pub.subscribe(self.put_session, "put_session")
        pub.subscribe(self.put_measurement, "put_measurement")
        pub.subscribe(self.put_contact, "put_contact")
        pub.subscribe(self.put_plate, "put_plate")
        # Various
        pub.subscribe(self.changed_settings, "changed_settings")

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


    def create_session(self, session):
        if not self.subject_id:
            pub.sendMessage("update_statusbar", status="Model.create_session: Subject not selected")
            pub.sendMessage("message_box", message="Please select a subject")
            raise settings.MissingIdentifier("Subject missing")

        # Check if the session isn't already in the table
        if self.sessions_table.get_session_row(session_name=session["session_name"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_session: Session already exists")
            return

        # How many sessions do we already have?
        session_id = self.sessions_table.get_new_id()
        session["session_id"] = session_id

        self.session_group = self.sessions_table.create_session(**session)
        pub.sendMessage("update_statusbar", status="Model.create_session: Session created")


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

    def create_contact(self, contact):
        contact_data = contact["data"]
        # Remove the key
        del contact["data"]

        if self.contacts_table.get_contact_row(contact_id=contact["contact_id"]).size:
            contact_group = self.contacts_table.update_contact(**contact)
            pub.sendMessage("update_statusbar", status="model.create_contact: Contact updated")
            return

        # If it doesn't already exist, we create the contact and store the data
        contact_group = self.contacts_table.create_contact(**contact)
        pub.sendMessage("update_statusbar", status="model.create_contact: Contact created")

        # These are all the results (for now) I want to add to the contact
        cop_x, cop_y = calculations.calculate_cop(contact_data)
        results = {"data": contact_data,
                   "max_of_max": contact_data.max(axis=2),
                   "force_over_time": calculations.force_over_time(contact_data),
                   "pressure_over_time": calculations.pressure_over_time(contact_data,
                                                                         sensor_surface=self.sensor_surface),
                   "surface_over_time": calculations.surface_over_time(contact_data,
                                                                       sensor_surface=self.sensor_surface),
                   "cop_x": cop_x,
                   "cop_y": cop_y
        }

        for item_id, data in results.items():
            if not self.contacts_table.get_data(group=contact_group, item_id=item_id):
                self.contacts_table.store_data(group=contact_group,
                                               item_id=item_id,
                                               data=data)
        pub.sendMessage("update_statusbar", status="model.create_contact: Contact data created")

    def create_plate(self, plate):
        """
        This function takes a plate dictionary object and stores it in PyTables
        """
        # Check if the plate is already in the table
        if self.plates_table.get_plate(brand=plate["brand"], model=plate["model"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_plate: Plate already exists")
            return

        # Create a subject id
        plate_id = self.plates_table.get_new_id()
        plate["plate_id"] = plate_id

        self.plates_table.create_plate(**plate)
        pub.sendMessage("update_statusbar", status="Model.create_plate: Plate created")

    def update_contact(self, contact):
        # Remove the key
        del contact["data"]
        contact_group = self.contacts_table.update_contact(**contact)
        pub.sendMessage("update_statusbar", status="model.create_contact: Contact updated")

    def store_contacts(self):
        if len(self.get_contact_data(self.measurement)) != len(self.contacts[self.measurement_name]):
            # TODO Check whether the number of contacts is equal to the number of contacts in the table
            raise Exception("Number of contacts doesn't match. Table needs to be dropped and newly inserted.")

        for contact in self.contacts[self.measurement_name]:
            contact = contact.to_dict()  # This takes care of some of the book keeping for us
            contact["subject_id"] = self.subject_id
            contact["session_id"] = self.session_id
            contact["measurement_id"] = self.measurement_id
            self.update_contact(contact)

        self.logger.info("Model.store_contacts: Results for {} have been successfully saved".format(
            self.measurement_name))
        pub.sendMessage("update_statusbar", status="Results saved")
        pub.sendMessage("stored_status", success=True)

        try:
            pass
        except Exception as e:
            self.logger.critical("Model.store_contacts: Storing failed! {}".format(e))
            pub.sendMessage("update_statusbar", status="Storing results failed!")
            pub.sendMessage("stored_status", success=False)

    def get_subjects(self, subject={}):
        subjects = self.subjects_table.get_subjects(**subject)
        pub.sendMessage("update_subjects_tree", subjects=subjects)

    def get_sessions(self, session={}):
        sessions = self.sessions_table.get_sessions(**session)
        pub.sendMessage("update_sessions_tree", sessions=sessions)

    def get_measurements(self, measurement={}):
        measurements = self.measurements_table.get_measurements(**measurement)
        pub.sendMessage("update_measurements_tree", measurements=measurements)
        # From one of the measurements, get its plate_id and call put_plate
        if measurements:
            # Update the plate information
            plate = self.plates[measurements[0]["plate_id"]]
            self.put_plate(plate)

    def get_contacts(self, contact={}):
        #contacts = self.contacts_table.get_contacts(**contact)
        if not self.contacts.get(self.measurement_name):
            contacts = self.get_contact_data(self.measurement)
            if not contacts:
                self.contacts[self.measurement_name] = self.track_contacts()
            else:
                self.contacts[self.measurement_name] = contacts
        pub.sendMessage("update_contacts_tree", contacts=self.contacts)
        # Check if we should update n_max everywhere
        self.update_n_max()


    def get_measurement_data(self):
        group = self.measurements_table.get_group(self.measurements_table.session_group,
                                                  self.measurement["measurement_id"])
        item_id = self.measurement_name
        self.measurement_data = self.measurements_table.get_data(group=group, item_id=item_id)
        pub.sendMessage("update_measurement_data", measurement_data=self.measurement_data)

    def get_contact_data(self, measurement):
        new_contacts = []
        measurement_id = measurement["measurement_id"]
        contact_data_table = table.ContactDataTable(database_file=self.database_file,
                                                    subject_id=self.subject_id,
                                                    session_id=self.session_id,
                                                    measurement_id=measurement_id)
        contacts_table = table.ContactsTable(database_file=self.database_file,
                                             subject_id=self.subject_id,
                                             session_id=self.session_id,
                                             measurement_id=measurement_id)
        # Get the rows from the table and their corresponding data
        contact_data = contact_data_table.get_contact_data()
        contacts = contacts_table.get_contacts()
        # Create Contact instances out of them
        for x, y in zip(contacts, contact_data):
            contact = contactmodel.Contact()
            # Restore it from the dictionary object
            # http://stackoverflow.com/questions/38987/how-can-i-merge-union-two-python-dictionaries-in-a-single-expression
            contact.restore(dict(x, **y))  # This basically merges the two dicts into one
            new_contacts.append(contact)
        return new_contacts

    def get_plates(self, plate={}):
        plates = self.plates_table.get_plates(**plate)
        pub.sendMessage("update_plates", plates=plates)

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

    def put_session(self, session):
        self.session = session
        self.session_id = session["session_id"]
        self.logger.info("Session ID set to {}".format(self.session_id))
        self.measurements_table = table.MeasurementsTable(database_file=self.database_file,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)
        pub.sendMessage("update_statusbar", status="Session: {}".format(self.session["session_name"]))

        self.get_measurements()
        # Load the contacts, but have it not send out anything
        self.load_contacts()
        # Next calculate the average based on the contacts
        self.calculate_average()
        # This needs to come after calculate average, perhaps refactor calculate_average into 2 functions?
        self.calculate_results()

    def put_measurement(self, measurement):
        self.measurement = measurement
        self.measurement_id = measurement["measurement_id"]
        self.measurement_name = measurement["measurement_name"]
        self.logger.info("Measurement ID set to {}".format(self.measurement_id))
        self.contacts_table = table.ContactsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)
        pub.sendMessage("update_statusbar", status="Measurement: {}".format(self.measurement_name))

    def put_contact(self, contact):
        self.contact = contact
        self.contact_id = contact["contact_id"]
        self.logger.info("Contact ID set to {}".format(self.contact_id))

    def put_plate(self, plate):
        self.plate = plate
        self.plate_id = plate["plate_id"]
        self.sensor_surface = self.plate["sensor_surface"]
        self.logger.info("Plate ID set to {}".format(self.plate_id))
        pub.sendMessage("update_plate", plate=self.plate)

    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.get_file_paths()
        pub.sendMessage("get_file_paths", file_paths=self.file_paths)

    def update_n_max(self):
        self.n_max = 0
        for m in self.measurements_table.measurements_table:
            n_max = m["maximum_value"]
            if n_max > self.n_max:
                self.n_max = n_max
        pub.sendMessage("update_n_max", n_max=self.n_max)

    def load_contacts(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        self.logger.info("Model.load_contacts: Loading all measurements for subject: {}, session: {}".format(
            self.subject_name, self.session["session_name"]))

        # Make sure self.contacts is empty
        self.contacts.clear()

        # Retrieve the brands and model
        plate = {}

        measurements = {}

        measurement_names = {}
        measurement = None
        for measurement in self.measurements_table.measurements_table:
            measurement_names[measurement["measurement_id"]] = measurement["measurement_name"]
            contacts = self.get_contact_data(measurement)
            if contacts:
                self.contacts[measurement["measurement_name"]] = contacts

            if not all([True if contact.contact_label < 0 else False for contact in contacts]):
                measurements[measurement["measurement_name"]] = measurement

        # # Check if the measurement isn't none, before trying to get an item
        # if measurement and measurement.__getitem__("plate_id"):
        #     plate["frequency"] = measurement["frequency"]
        #     self.put_plate(plate)
        # # If there are measurements, but they lack a plate
        # elif len(self.measurements_table.measurements_table) > 0:
        #     self.logger.warning("model.load_contacts: Measurement(s) lack plate")

        pub.sendMessage("update_measurement_status", measurements=measurements)

    def repeat_track_contacts(self):
        self.contacts[self.measurement_name] = self.track_contacts()
        pub.sendMessage("update_contacts_tree", contacts=self.contacts)

    #@profile
    def track_contacts(self):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        # Add padding to the measurement
        x = self.measurement["number_of_rows"]
        y = self.measurement["number_of_columns"]
        z = self.measurement["number_of_frames"]
        padding_factor = self.settings.padding_factor()
        data = np.zeros((x + 2 * padding_factor, y + 2 * padding_factor, z), np.float32)
        data[padding_factor:-padding_factor, padding_factor:-padding_factor, :] = self.measurement_data
        raw_contacts = tracking.track_contours_graph(data)

        contacts = []
        # Convert them to class objects
        for index, raw_contact in enumerate(raw_contacts):
            contact = contactmodel.Contact()
            contact.create_contact(contact=raw_contact,
                                   measurement_data=self.measurement_data,
                                   padding=padding_factor,
                                   orientation=self.measurement["orientation"])
            contact.calculate_results(sensor_surface=self.sensor_surface)
            # Give each contact the same orientation as the measurement it originates from
            contact.set_orientation(self.measurement["orientation"])
            # Skip contacts that have only been around for one frame
            if len(contact.frames) > 1:
                contacts.append(contact)

        # Sort the contacts based on their position along the first dimension
        contacts = sorted(contacts, key=lambda contact: contact.min_z)
        # Update their index
        for contact_id, contact in enumerate(contacts):
            contact.set_contact_id(contact_id)

        status = "Number of contacts found: {}".format(len(contacts))
        pub.sendMessage("update_statusbar", status=status)
        return contacts

    def update_current_contact(self, current_contact_index, contacts):
        # I wonder if this gets mutated by processing widget, in which case I don't have to pass it here
        self.contacts = contacts
        self.current_contact_index = current_contact_index

        self.calculate_average()

        pub.sendMessage("updated_current_contact", contacts=self.contacts,
                        current_contact_index=self.current_contact_index)

    # TODO see when this function is being called and make sure it doesn't happen unnecessarily
    def calculate_average(self):
        # Empty average measurement_data
        self.average_data.clear()
        self.data_list = defaultdict(list)

        mx = 0
        my = 0
        mz = 0
        # Group all the measurement_data per contact
        for measurement_name, contacts in self.contacts.items():
            for contact in contacts:
                contact_label = contact.contact_label
                if contact_label >= 0:
                    self.data_list[contact_label].append(contact.data)

                x, y, z = contact.data.shape
                if x > mx:
                    mx = x
                if y > my:
                    my = y
                if z > mz:
                    mz = z

        shape = (mx, my, mz)
        pub.sendMessage("update_shape", shape=shape)
        # Then get the normalized measurement_data
        for contact_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data, shape)
            self.average_data[contact_label] = normalized_data

        pub.sendMessage("update_average", average_data=self.average_data)

    # TODO Why are we calculating stuff? These things are already stored, so be lazy and load them!
    def calculate_results(self):
        # If we don't have any data, its no use to try and calculate something
        if len(self.data_list.keys()) == 0:
            return

        self.results.clear()
        self.max_results.clear()

        for contact_label, data_list in self.data_list.items():
            self.results[contact_label]["filtered"] = utility.filter_outliers(data_list, contact_label)
            for data in data_list:
                force = calculations.force_over_time(data)
                self.results[contact_label]["force"].append(force)
                max_force = np.max(force)
                if max_force > self.max_results.get("force", 0):
                    self.max_results["force"] = max_force

                pressure = calculations.pressure_over_time(data, sensor_surface=self.sensor_surface)
                self.results[contact_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > self.max_results.get("pressure", 0):
                    self.max_results["pressure"] = max_pressure

                surface = calculations.surface_over_time(data, sensor_surface=self.sensor_surface)
                self.results[contact_label]["surface"].append(surface)
                max_surface = np.max(surface)
                if max_surface > self.max_results.get("surface", 0):
                    self.max_results["surface"] = max_surface

                cop_x, cop_y = calculations.calculate_cop(data)
                self.results[contact_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > self.max_results.get("duration", 0):
                    self.max_results["duration"] = max_duration

        pub.sendMessage("update_results", results=self.results, max_results=self.max_results)


    def clear_cached_values(self):
        self.logger.info("Model.clear_cached_values")
        self.session = {}
        self.measurement = {}
        self.contact = {}
        self.brand = {}
        self.subject_name = ""
        self.measurement_name = ""
        self.session_id = ""
        self.subject_id = ""
        self.average_data.clear()
        self.contacts.clear()
        self.results.clear()
        self.max_results.clear()
        self.n_max = 0
        pub.sendMessage("clear_cached_values")

    def changed_settings(self):
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()