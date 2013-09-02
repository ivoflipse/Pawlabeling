from collections import defaultdict
import logging
import os
import numpy as np
from pubsub import pub
from pawlabeling.functions import utility, io, tracking, calculations
from pawlabeling.settings import configuration
from pawlabeling.models import contactmodel, tabelmodel


class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder

        self.subjects_table = tabelmodel.SubjectsTable()

        self.subject_name = ""
        self.measurement_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.data_list = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()

        self.logger = logging.getLogger("logger")

        # OLD
        #pub.subscribe(self.load_file, "load_file")
        pub.subscribe(self.load_results, "load_results")
        pub.subscribe(self.update_current_contact, "update_current_contact")
        pub.subscribe(self.store_status, "store_status")
        pub.subscribe(self.track_contacts, "track_contacts")
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

    def create_measurement(self, measurement):
        measurement_name = measurement["measurement_name"]
        file_path = measurement["file_path"]

        measurement["subject_id"] = self.subject_id
        measurement["session_id"] = self.session_id

        # Check if the file is zipped or not and extract the raw measurement_data
        if measurement_name[-3:] == "zip":
            # Unzip the file
            input_file = io.open_zip_file(file_path)
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
        measurement["orientation"] = io.check_orientation(data)  # TODO This function seems to be incorrect somehow!
        measurement["maximum_value"] = data.max()  # Perhaps round this and store it as an int?
        # Store the file_name without the .zip

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

    def create_contact(self, contacts):
        # TODO You might want to check if the contact_id key is present and that each contact is a dictionary
        # We'll track the contact groups using this contact_ids dictionary
        self.contact_ids = {}
        for contact in contacts:
            try:
                contact_group = self.contacts_table.create_contact(**contact)
                self.contact_ids[contact_group._v_name] = contact_group
            except MissingIdentifier:
                self.logger.warning("Model.create_contact: Some of the required fields are missing")

    def get_subjects(self, subject):
        subjects = self.subjects_table.get_subjects(**subject)
        pub.sendMessage("update_subjects_tree", subjects=subjects)

    def get_sessions(self, session):
        sessions = self.sessions_table.get_sessions(**session)
        pub.sendMessage("update_sessions_tree", sessions=sessions)

    def get_measurements(self, measurement):
        measurements = self.measurements_table.get_measurements(**measurement)
        pub.sendMessage("update_measurements_tree", measurements=measurements)

    def get_contacts(self, contact):
        contacts = self.contacts_table.get_contacts(**contact)
        pub.sendMessage("update_contacts_tree", contacts=contacts)

    def get_measurement_data(self, data):
        group = self.measurements_table.get_group(self.measurements_table.session_group,
                                                  self.measurement["measurement_id"])
        self.measurement_data = self.measurements_table.get_data(group, item_id=data["item_id"])
        pub.sendMessage("update_measurement_data", measurement_data=self.measurement_data)

    def put_subject(self, subject):
        self.subject = subject
        self.subject_id = subject["subject_id"]
        self.logger.info("Subject ID set to {}".format(self.subject_id))
        # As soon as a subject is selected, we instantiate our sessions table
        self.sessions_table = tabelmodel.SessionsTable(subject_id=self.subject_id)

    def put_session(self, session):
        self.session = session
        self.session_id = session["session_id"]
        self.logger.info("Session ID set to {}".format(self.session_id))
        self.measurements_table = self.measurements_table = tabelmodel.MeasurementsTable(subject_id=self.subject_id,
                                                                                         session_id=self.session_id)

    def put_measurement(self, measurement):
        self.measurement = measurement
        self.measurement_id = measurement["measurement_id"]
        self.logger.info("Measurement ID set to {}".format(self.measurement_id))
        self.contacts_table = tabelmodel.ContactsTable(subject_id=self.subject_id,
                                                       session_id=self.session_id,
                                                       measurement_id=self.measurement_id)

    def put_contact(self, contact):
        self.contact = contact
        self.contact_id = contact["contact_id"]
        self.logger.info("Contact ID set to {}".format(self.contact_id))
        # I probably need to load stuff from this contacts group, perhaps GET it?


    ##################################################################################################################

    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.get_file_paths()
        pub.sendMessage("get_file_paths", file_paths=self.file_paths)


    # def load_file(self, measurement):
    #     self.measurement = measurement
    #     # Log which measurement we're loading
    #     subject_name = "{} {}".format(self.subject["first_name"], self.subject["last_name"])
    #     measurement_name = measurement["measurement_name"]
    #     self.logger.info("Model.load_file: Loading measurement for subject: {} {} - {}".format(subject_name,
    #                                                                                     measurement_name))
    #
    #     # Get the measurement_data
    #
    #     measurement[""]
    #
    #     # Notify the widgets that there's a new n_max available
    #     pub.sendMessage("update_n_max", n_max=self.n_max)
    #     # Notify the widgets that a new measurement is available
    #     pub.sendMessage("loaded_file", measurement=self.measurement, measurement_name=self.measurement_name,
    #                     shape=self.measurement.shape)

    def load_results(self, widget):
        self.load_all_results()
        if widget == "processing":
            pub.sendMessage("processing_results", contacts=self.contacts, average_data=self.average_data)
        elif widget == "analysis":
            # If there's no data_list, there are no labeled contacts to display
            if self.data_list.keys():
                pub.sendMessage("analysis_results", contacts=self.contacts, average_data=self.average_data,
                                results=self.results, max_results=self.max_results)

    def load_all_results(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        self.logger.info("Model.load_all_results: Loading all results for subject: {}".format(self.subject_name))
        # Make sure self.contacts is empty
        self.contacts.clear()

        for measurement_name in self.file_paths[self.subject_name]:
            input_path = io.find_stored_file(self.subject_name, measurement_name)
            contacts = io.load_results(input_path)
            # Did we get any results?
            if contacts:
                self.contacts[measurement_name] = contacts
                # Check if any of the contacts has a higher n_max
                for contact in contacts:
                    n_max = np.max(contact.data)
                    if n_max > self.n_max:
                        self.n_max = n_max

        pub.sendMessage("update_n_max", n_max=self.n_max)

        if not self.contacts.get(self.measurement_name):
            self.track_contacts()

        # Calculate the average, after everything has been loaded
        self.calculate_average()
        self.calculate_results()


    def track_contacts(self):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        # Add padding to the measurement
        x, y, z = self.measurement.shape
        padding = configuration.padding_factor
        data = np.zeros((x + 2 * padding, y + 2 * padding, z), np.float32)
        data[padding:-padding, padding:-padding, :] = self.measurement
        contacts = tracking.track_contours_graph(data)

        # Make sure we don't have any contacts stored if we're tracking again
        # I'd suggest moving the calculation of average_data out, so I can update it every time I label a contact
        self.contacts[self.measurement_name] = []

        # Convert them to class objects
        for index, raw_contact in enumerate(contacts):
            contact = contactmodel.Contact()
            contact.create_contact(contact=raw_contact, measurement_data=self.measurement, padding=1)
            # Skip contacts that have only been around for one frame
            if len(contact.frames) > 1:
                self.contacts[self.measurement_name].append(contact)

        # Sort the contacts based on their position along the first dimension
        self.contacts[self.measurement_name] = sorted(self.contacts[self.measurement_name],
                                                      key=lambda contact: contact.min_z)
        # Update their index
        for index, contact in enumerate(self.contacts[self.measurement_name]):
            contact.set_index(index)

        status = "Number of contacts found: {}".format(len(self.contacts[self.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)

    def update_current_contact(self, current_contact_index, contacts):
        # I wonder if this gets mutated by processing widget, in which case I don't have to pass it here
        self.contacts = contacts
        self.current_contact_index = current_contact_index
        # Refresh the average measurement_data
        self.calculate_average()

        pub.sendMessage("updated_current_contact", contacts=self.contacts, average_data=self.average_data,
                        current_contact_index=self.current_contact_index)

    def calculate_average(self):
        # Empty average measurement_data
        self.average_data.clear()
        self.data_list.clear()
        # Group all the measurement_data per contact
        for measurement_name, contacts in self.contacts.items():
            for contact in contacts:
                contact_label = contact.contact_label
                if contact_label >= 0:
                    self.data_list[contact_label].append(contact.data)

        # Then get the normalized measurement_data
        for contact_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data)
            self.average_data[contact_label] = normalized_data

    def calculate_results(self):
        self.results.clear()
        self.max_results.clear()
        self.filtered = defaultdict()

        for contact_label, data_list in self.data_list.items():
            self.results[contact_label]["filtered"] = utility.filter_outliers(data_list, contact_label)
            self.filtered[contact_label] = utility.filter_outliers(data_list, contact_label)
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

                    # for measurement_name, contacts in self.contacts.items():
                    #     for contact in self.contacts:


    def store_status(self):
        """
        This function creates a file in the store_results_folder and create the folder if it doesn't exist
        It will notify the status bar, log and return a boolean value depending on the success or failure of execution
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io.create_results_folder(self.subject_name)
        # Try storing the results
        try:
            pickle_path = os.path.join(self.new_path, self.measurement_name)
            io.results_to_pickle(pickle_path, self.contacts[self.measurement_name])
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
        self.average_data.clear()
        self.contacts.clear()
        self.data_list.clear()
        self.results.clear()
        self.max_results.clear()
        pub.sendMessage("clear_cached_values")


class MissingIdentifier(Exception):
    pass