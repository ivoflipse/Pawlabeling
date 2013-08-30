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

        self.dog_name = ""
        self.measurement_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.paws = defaultdict(list)
        self.data_list = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()

        self.logger = logging.getLogger("logger")

        pub.subscribe(self.switch_dogs, "switch_dogs")
        pub.subscribe(self.switch_measurements, "switch_measurements")
        pub.subscribe(self.load_file, "load_file")
        pub.subscribe(self.load_results, "load_results")
        pub.subscribe(self.update_current_paw, "update_current_paw")
        pub.subscribe(self.store_status, "store_status")
        pub.subscribe(self.track_contacts, "track_contacts")

        pub.subscribe(self.create_subject, "create_subject")
        pub.subscribe(self.create_session, "create_session")
        pub.subscribe(self.create_measurement, "create_measurement")
        pub.subscribe(self.create_contact, "create_contact")

        pub.subscribe(self.get_new_subject_id, "get_new_subject_id")

    def create_subject(self, subject):
        """
        This function takes a subject dictionary object and stores it in PyTables
        """
        try:
            self.subjects_table.create_subject(**subject)
        except MissingIdentifier:
            self.logger.warning("Model.create_subject: Some of the required fields are missing")

    def create_session(self, session):
        # So how do I get the subject_id?!?
        subject_id = "subject_0"
        self.sessions_table = tabelmodel.SessionsTable(subject_id=subject_id)
        try:
            self.sessions_table.create_session(**session)
        except MissingIdentifier:
            self.logger.warning("Model.create_session: Some of the required fields are missing")

    def create_measurement(self, measurement):
        subject_id = "subject_0"
        session_id = "session_0"
        self.measurements_table = tabelmodel.MeasurementsTable(subject_id=subject_id, session_id=session_id)
        try:
            self.measurements_table.create_measurement(**measurement)
        except MissingIdentifier:
            self.logger.warning("Model.create_measurement: Some of the required fields are missing")

    def create_contact(self, contacts):
        subject_id = "subject_0"
        session_id = "session_0"
        measurement_id = "measurement_0"
        self.contacts_table = tabelmodel.ContactsTable(subject_id=subject_id, session_id=session_id,
                                                       measurement_id=measurement_id)

        # TODO You might want to check if the contact_id key is present and that each contact is a dictionary
        for contact in contacts:
            try:
                self.contacts_table.create_contact(**contact)
            except MissingIdentifier:
                self.logger.warning("Model.create_contact: Some of the required fields are missing")

    def get_new_subject_id(self):
        subject_count = len(self.subjects_table.subjects_table)
        pub.sendMessage("update_subject_id", subject_id="subject_{}".format(subject_count))

    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.get_file_paths()
        pub.sendMessage("get_file_paths", file_paths=self.file_paths)

    def switch_dogs(self, dog_name):
        """
        This function should always be called when you want to access other dog's results
        """
        if dog_name != self.dog_name:
            self.logger.info(
                "Model.switch_dogs: Switching dogs from {} to {}".format(self.dog_name, dog_name))
            self.dog_name = dog_name

            # If switching dogs, we also want to clear our caches, because those values are useless
            self.clear_cached_values()

    def switch_measurements(self, measurement_name):
        """
        This function should always be called when you want to access a new measurement
        """
        if measurement_name != self.measurement_name:
            self.logger.info(
                "Model.switch_measurements: Switching measurements to {}".format(measurement_name))
            self.measurement_name = measurement_name

    def load_file(self):
        # Get the path from the file_paths dictionary
        self.file_path = self.file_paths[self.dog_name][self.measurement_name]

        # Log which measurement we're loading
        self.logger.info("Model.load_file: Loading measurement for dog: {} - {}".format(self.dog_name,
                                                                                        self.measurement_name))
        # Pass the new measurement through to the widget
        self.measurement = io.load(self.file_path)
        # Check the orientation of the plate and make sure its left to right
        self.measurement = io.fix_orientation(self.measurement)
        # Get the number of frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        # Get the normalizing factor for the color bars
        self.n_max = self.measurement.max()

        # Notify the widgets that there's a new n_max available
        pub.sendMessage("update_n_max", n_max=self.n_max)
        # Notify the widgets that a new measurement is available
        pub.sendMessage("loaded_file", measurement=self.measurement, measurement_name=self.measurement_name,
                        shape=self.measurement.shape)

    def load_results(self, widget):
        self.load_all_results()
        if widget == "processing":
            pub.sendMessage("processing_results", paws=self.paws, average_data=self.average_data)
        elif widget == "analysis":
            # If there's no data_list, there are no labeled paws to display
            if self.data_list.keys():
                pub.sendMessage("analysis_results", paws=self.paws, average_data=self.average_data,
                                results=self.results, max_results=self.max_results)

    def load_all_results(self):
        """
        Check if there if any measurements for this dog have already been processed
        If so, retrieve the data and convert them to a usable format
        """
        self.logger.info("Model.load_all_results: Loading all results for dog: {}".format(self.dog_name))
        # Make sure self.paws is empty
        self.paws.clear()

        for measurement_name in self.file_paths[self.dog_name]:
            input_path = io.find_stored_file(self.dog_name, measurement_name)
            paws = io.load_results(input_path)
            # Did we get any results?
            if paws:
                self.paws[measurement_name] = paws
                # Check if any of the paws has a higher n_max
                for paw in paws:
                    n_max = np.max(paw.data)
                    if n_max > self.n_max:
                        self.n_max = n_max

        pub.sendMessage("update_n_max", n_max=self.n_max)

        if not self.paws.get(self.measurement_name):
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
        paws = tracking.track_contours_graph(data)

        # Make sure we don't have any paws stored if we're tracking again
        # I'd suggest moving the calculation of average_data out, so I can update it every time I label a paw
        self.paws[self.measurement_name] = []

        # Convert them to class objects
        for index, raw_paw in enumerate(paws):
            paw = contactmodel.Contact()
            paw.create_contact(contact=raw_paw, measurement_data=self.measurement, padding=1)
            # Skip paws that have only been around for one frame
            if len(paw.frames) > 1:
                self.paws[self.measurement_name].append(paw)

        # Sort the contacts based on their position along the first dimension
        self.paws[self.measurement_name] = sorted(self.paws[self.measurement_name], key=lambda paw: paw.min_z)
        # Update their index
        for index, paw in enumerate(self.paws[self.measurement_name]):
            paw.set_index(index)

        status = "Number of paws found: {}".format(len(self.paws[self.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)

    def update_current_paw(self, current_paw_index, paws):
        # I wonder if this gets mutated by processing widget, in which case I don't have to pass it here
        self.paws = paws
        self.current_paw_index = current_paw_index
        # Refresh the average data
        self.calculate_average()

        pub.sendMessage("updated_current_paw", paws=self.paws, average_data=self.average_data,
                        current_paw_index=self.current_paw_index)

    def calculate_average(self):
        # Empty average data
        self.average_data.clear()
        self.data_list.clear()
        # Group all the data per paw
        for measurement_name, paws in self.paws.items():
            for paw in paws:
                paw_label = paw.paw_label
                if paw_label >= 0:
                    self.data_list[paw_label].append(paw.data)

        # Then get the normalized data
        for paw_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data)
            self.average_data[paw_label] = normalized_data

    def calculate_results(self):
        self.results.clear()
        self.max_results.clear()
        self.filtered = defaultdict()

        for paw_label, data_list in self.data_list.items():
            self.results[paw_label]["filtered"] = utility.filter_outliers(data_list, paw_label)
            self.filtered[paw_label] = utility.filter_outliers(data_list, paw_label)
            for data in data_list:
                force = calculations.force_over_time(data)
                self.results[paw_label]["force"].append(force)
                max_force = np.max(force)
                if max_force > self.max_results.get("force", 0):
                    self.max_results["force"] = max_force

                pressure = calculations.pressure_over_time(data)
                self.results[paw_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > self.max_results.get("pressure", 0):
                    self.max_results["pressure"] = max_pressure

                cop_x, cop_y = calculations.calculate_cop(data)
                self.results[paw_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > self.max_results.get("duration", 0):
                    self.max_results["duration"] = max_duration

                    # for measurement_name, paws in self.paws.items():
                    #     for paw in self.paws:


    def store_status(self):
        """
        This function creates a file in the store_results_folder and create the folder if it doesn't exist
        It will notify the status bar, log and return a boolean value depending on the success or failure of execution
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io.create_results_folder(self.dog_name)
        # Try storing the results
        try:
            pickle_path = os.path.join(self.new_path, self.measurement_name)
            io.results_to_pickle(pickle_path, self.paws[self.measurement_name])
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
        self.paws.clear()
        self.data_list.clear()
        self.results.clear()
        self.max_results.clear()
        pub.sendMessage("clear_cached_values")


class MissingIdentifier(Exception):
    pass