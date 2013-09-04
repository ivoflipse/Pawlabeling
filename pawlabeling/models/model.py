from collections import defaultdict
import logging
import os
import numpy as np
from pubsub import pub
from pawlabeling.functions import utility, io, tracking, calculations
from pawlabeling.settings import configuration
from pawlabeling.models import contactmodel, table
#from memory_profiler import profile


class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.database_file = configuration.database_file

        self.subjects_table = table.SubjectsTable(database_file=self.database_file)

        self.subject_name = ""
        self.measurement_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()

        self.logger = logging.getLogger("logger")

        # OLD
        pub.subscribe(self.load_contacts, "load_contacts")
        pub.subscribe(self.update_current_contact, "update_current_contact")
        pub.subscribe(self.store_status, "store_status")
        pub.subscribe(self.repeat_track_contacts, "track_contacts")
        pub.subscribe(self.calculate_results, "calculate_results")
        # CREATE
        pub.subscribe(self.create_subject, "create_subject")
        pub.subscribe(self.create_session, "create_session")
        pub.subscribe(self.create_measurement, "create_measurement")
        pub.subscribe(self.create_contact, "create_contact")
        # GET
        pub.subscribe(self.get_subjects, "get_subjects")
        pub.subscribe(self.get_sessions, "get_sessions")
        pub.subscribe(self.get_measurements, "get_measurements")
        pub.subscribe(self.get_contacts, "get_contacts")
        pub.subscribe(self.get_measurement_data, "get_measurement_data")
        # PUT
        pub.subscribe(self.put_subject, "put_subject")
        pub.subscribe(self.put_session, "put_session")
        pub.subscribe(self.put_measurement, "put_measurement")
        pub.subscribe(self.put_contact, "put_contact")

    def create_subject(self, subject):
        """
        This function takes a subject dictionary object and stores it in PyTables
        """
        try:
            self.subject_group = self.subjects_table.create_subject(**subject)
        except MissingIdentifier:
            self.logger.warning("Model.create_subject: Some of the required fields are missing")

    def create_session(self, session):
        try:
            self.session_group = self.sessions_table.create_session(**session)
        except MissingIdentifier:
            self.logger.warning("Model.create_session: Some of the required fields are missing")

    # TODO consider moving this to a Measurement class
    def create_measurement(self, measurement):
        measurement_name = measurement["measurement_name"]
        file_path = measurement["file_path"]

        measurement["subject_id"] = self.subject_id
        measurement["session_id"] = self.session_id

        # Check if the file is zipped or not and extract the raw measurement_data
        if measurement_name[-3:] == "zip":
            # Unzip the file
            input_file = io.open_zip_file(file_path)
            # Store the file_name without the .zip
            measurement["measurement_name"] = measurement_name[:-4]  # Store without the zip part please
        else:
            with open(file_path, "r") as infile:
                input_file = infile.read()

            # If the user wants us to zip it, zip it so they don't keep taking up so much space!
            if configuration.zip_files:
                io.zip_file(configuration.measurement_folder, measurement_name)

        # Extract the measurement_data
        data = io.load(input_file, brand=measurement["brand"])
        number_of_rows, number_of_cols, number_of_frames = data.shape
        measurement["number_of_rows"] = number_of_rows
        measurement["number_of_cols"] = number_of_cols
        measurement["number_of_frames"] = number_of_frames
        measurement["orientation"] = io.check_orientation(data)
        measurement["maximum_value"] = data.max()  # Perhaps round this and store it as an int?

        # We're not going to store this, so we delete the key
        del measurement["file_path"]

        try:
            self.measurement_group = self.measurements_table.create_measurement(**measurement)
            # Don't forget to store the measurement_data for the measurement as well!
            self.measurements_table.store_data(group=self.measurement_group,
                                               item_id=measurement["measurement_name"],
                                               data=data)
        except MissingIdentifier:
            self.logger.warning("Model.create_measurement: Some of the required fields are missing")

    def create_contact(self, contact):
        try:
            contact_data = contact["data"]
            # Remove the key
            del contact["data"]
            self.contact_group = self.contacts_table.create_contact(**contact)

            # These are all the results (for now) I want to add to the contact
            results = {"data": contact_data,
                       "max_of_max": contact_data.max(axis=2),
                       "force_over_time": calculations.force_over_time(contact_data),
                       "pressure_over_time": calculations.pressure_over_time(contact_data),
                       "surface_over_time": calculations.surface_over_time(contact_data),
                       "cop_x": calculations.calculate_cop(contact_data)[0],
                       "cop_y": calculations.calculate_cop(contact_data)[1]}  # Uhoh, this is expensive...

            for item_id, data in results.items():
                # Check if it doesn't already exist
                if not self.contacts_table.get_data(group=self.contact_group, item_id=item_id):
                    self.contacts_table.store_data(group=self.contact_group,
                                                   item_id=item_id,
                                                   data=data)
        except MissingIdentifier:
            self.logger.warning("Model.create_contacts: Some of the required fields are missing")

    def get_subjects(self, subject={}):
        subjects = self.subjects_table.get_subjects(**subject)
        pub.sendMessage("update_subjects_tree", subjects=subjects)

    def get_sessions(self, session={}):
        sessions = self.sessions_table.get_sessions(**session)
        pub.sendMessage("update_sessions_tree", sessions=sessions)

    def get_measurements(self, measurement={}):
        measurements = self.measurements_table.get_measurements(**measurement)
        pub.sendMessage("update_measurements_tree", measurements=measurements)

    def get_contacts(self, contact={}):
        #contacts = self.contacts_table.get_contacts(**contact)
        if not self.contacts.get(self.measurement_name):
            contacts = self.get_contact_data(self.measurement)
            if not contacts:
                self.contacts[self.measurement_name] = self.track_contacts()
            else:
                self.contacts[self.measurement_name] = contacts
        pub.sendMessage("update_contacts_tree", contacts=self.contacts)

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
        contact_data = contact_data_table.get_data()
        contacts = contacts_table.get_contacts()
        # Create Contact instances out of them
        for x, y in zip(contacts, contact_data):
            contact = contactmodel.Contact()
            # Restore it from the dictionary object
            # http://stackoverflow.com/questions/38987/how-can-i-merge-union-two-python-dictionaries-in-a-single-expression
            contact.restore(dict(x, **y))  # This basically merges the two dicts into one
            new_contacts.append(contact)
        return new_contacts

    def put_subject(self, subject):
        #print "model.put_subject"
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
        # Whenever we switch sessions, clear the cache
        self.clear_cached_values()

        #print "model.put_session"
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

    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.get_file_paths()
        pub.sendMessage("get_file_paths", file_paths=self.file_paths)

    def load_contacts(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        self.logger.info("Model.load_contacts: Loading all measurements for subject: {}, session: {}".format(
            self.subject_name, self.session["session_name"]))

        # Make sure self.contacts is empty
        self.contacts.clear()
        self.n_max = 0

        measurement_names = {}
        for m in self.measurements_table.measurements_table:
            measurement_names[m["measurement_id"]] = m["measurement_name"]
            n_max = m["maximum_value"]
            if n_max > self.n_max:
                self.n_max = n_max

            contacts = self.get_contact_data(m)
            if contacts:
                self.contacts[m["measurement_name"]] = contacts

        # Calculate the highest n_max and publish that
        pub.sendMessage("update_n_max", n_max=self.n_max)
        #pub.sendMessage("update_contacts", contacts=self.contacts)
        # These two messages could pretty much be consolidated, possibly even the one above
        #pub.sendMessage("processing_results", contacts=self.contacts, average_data=self.average_data)
        #pub.sendMessage("update_contacts_tree", contacts=self.contacts)

    def repeat_track_contacts(self):
        self.contacts[self.measurement_name] = self.track_contacts()
        pub.sendMessage("update_contacts_tree", contacts=self.contacts)


    #@profile
    def track_contacts(self):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        # Add padding to the measurement
        x = self.measurement["number_of_rows"]
        y = self.measurement["number_of_cols"]
        z = self.measurement["number_of_frames"]
        padding = configuration.padding_factor
        data = np.zeros((x + 2 * padding, y + 2 * padding, z), np.float32)
        data[padding:-padding, padding:-padding, :] = self.measurement_data
        raw_contacts = tracking.track_contours_graph(data)

        contacts = []
        # Convert them to class objects
        for index, raw_contact in enumerate(raw_contacts):
            contact = contactmodel.Contact()
            contact.create_contact(contact=raw_contact,
                                   measurement_data=self.measurement_data,
                                   padding=padding,
                                   orientation=self.measurement["orientation"])
            contact.calculate_results()
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

    def calculate_average(self):
        #print "model.calculate_average"
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
        # Then get the normalized measurement_data
        for contact_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data, shape)
            self.average_data[contact_label] = normalized_data

        pub.sendMessage("update_average", average_data=self.average_data)

    def calculate_results(self):
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

                pressure = calculations.pressure_over_time(data)
                self.results[contact_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > self.max_results.get("pressure", 0):
                    self.max_results["pressure"] = max_pressure

                cop_x, cop_y = calculations.calculate_cop(data)
                self.results[contact_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > self.max_results.get("duration", 0):
                    self.max_results["duration"] = max_duration

        pub.sendMessage("update_results", results=self.results, max_results=self.max_results)

    def store_status(self):
        for contact in self.contacts[self.measurement_name]:
            contact = contact.to_dict()  # This takes care of some of the book keeping for us
            contact["subject_id"] = self.subject_id
            contact["session_id"] = self.session_id
            contact["measurement_id"] = self.measurement_id
            self.create_contact(contact)

        try:
            self.logger.info("Model.store_status: Results for {} have been successfully saved".format(
                self.measurement_name))
            pub.sendMessage("update_statusbar", status="Results saved")
            pub.sendMessage("stored_status", success=True)
        except Exception as e:
            self.logger.critical("Model.store_status: Storing failed! {}".format(e))
            pub.sendMessage("update_statusbar", status="Storing results failed!")
            pub.sendMessage("stored_status", success=False)


    def clear_cached_values(self):
        self.logger.info("Model.clear_cached_values")
        #self.subject = {} # Not if we clear from put_session
        self.session = {}
        self.measurement = {}
        self.contact = {}
        self.average_data.clear()
        self.contacts.clear()
        self.results.clear()
        self.max_results.clear()
        pub.sendMessage("clear_cached_values")


class MissingIdentifier(Exception):
    pass