from collections import defaultdict
import numpy as np
from settings import configuration
from contactmodel import Contact
from functions import io, tracking, utility, calculations
from functions.pubsub import pub
import logging

class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder

        self.dog_name = ""
        self.measurement_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.paw_data = defaultdict(list)
        self.paw_labels = defaultdict(dict)
        self.paws = defaultdict(list)
        self.data_list = defaultdict(list)

        self.logger = logging.getLogger("logger")

        pub.subscribe(self.switch_dogs, "switch_dogs")
        pub.subscribe(self.switch_measurements, "switch_measurements")
        pub.subscribe(self.load_file, "load_file")
        pub.subscribe(self.load_results, "load_results")
        pub.subscribe(self.update_current_paw, "update_current_paw")
        pub.subscribe(self.store_status, "store_status")
        pub.subscribe(self.track_contacts, "track_contacts")

    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.load_file_paths()
        pub.sendMessage("load_file_paths", file_paths=self.file_paths)

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
            pub.sendMessage("processing_results", paws=self.paws, paw_labels=self.paw_labels,
                            paw_data=self.paw_data, average_data=self.average_data)
        elif widget == "analysis":
            pub.sendMessage("analysis_results", paws=self.paws, paw_labels=self.paw_labels, paw_data=self.paw_data,
                            average_data=self.average_data, results=self.results, max_results=self.max_results)

    def load_all_results(self):
        """
        Check if there if any measurements for this dog have already been processed
        If so, retrieve the data and convert them to a usable format
        """
        self.logger.info("Model.load_all_results: Loading all results for dog: {}".format(self.dog_name))
        for measurement_name in self.file_paths[self.dog_name]:
            # Refresh the cache, it might be stale
            if measurement_name in self.paws:
                self.paws[measurement_name] = []
                self.paw_labels[measurement_name] = {}
                self.paw_data[measurement_name] = []

            stored_results = io.load_results(self.dog_name, measurement_name)
            # If we have results, stick them in their respective variable
            if stored_results:
                self.paw_labels[measurement_name] = stored_results["paw_labels"]
                for index, paw_data in stored_results["paw_data"].items():
                    self.paw_data[measurement_name].append(paw_data)

                    # Check if n_max happens to be larger here
                    max_data = np.max(paw_data)
                    if max_data > self.n_max:
                        self.n_max = max_data

                    paw = utility.Contact(stored_results["paw_results"][index], restoring=True)
                    self.paws[measurement_name].append(paw)

                # Until I've moved everything to be dictionary based, here's code to sort the paws + paw_data
                # Fancy pants code found here:
                # http://stackoverflow.com/questions/9764298/is-it-possible-to-sort-two-listswhich-reference-each-other-in-the-exact-same-w
                self.paws[measurement_name], self.paw_data[measurement_name] = zip(*sorted(
                    zip(self.paws[measurement_name], self.paw_data[measurement_name]),
                    key=lambda pair: pair[0].frames[0]))

        # Note: this updates n_max if there ever was a higher n_max, also applies to the entire plate!
        pub.sendMessage("update_n_max", n_max=self.n_max)

        if not self.paw_data[self.measurement_name]:
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
        self.paw_labels[self.measurement_name] = {}
        self.paw_data[self.measurement_name] = []

        # Convert them to class objects
        for index, paw in enumerate(paws):
            paw = Contact(paw, padding=1)
            paw.convert_contour_to_slice(self.measurement)
            # Skip paws that have only been around for one frame
            if len(paw.frames) > 1:
                self.paws[self.measurement_name].append(paw)

        # Sort the contacts based on their position along the first dimension
        self.paws[self.measurement_name] = sorted(self.paws[self.measurement_name], key=lambda paw: paw.frames[0])

        for index, paw in enumerate(self.paws[self.measurement_name]):
            data_slice = utility.convert_contour_to_slice(self.measurement, paw.contour_list)
            self.paw_data[self.measurement_name].append(data_slice)
            # I've made -2 the label for unlabeled paws, -1 == unlabeled + selected
            paw_label = -2
            # Test if the paw touches the edge of the plate
            if utility.touches_edges(self.measurement, paw):
                paw_label = -3  # Mark it as invalid
            elif utility.incomplete_step(data_slice):
                paw_label = -3
            self.paw_labels[self.measurement_name][index] = paw_label

        status = "Number of paws found: {}".format(len(self.paws[self.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)

    def update_current_paw(self, current_paw_index, paw_labels):
        self.paw_labels = paw_labels
        self.current_paw_index = current_paw_index
        # Refresh the average data
        self.calculate_average()

        pub.sendMessage("updated_current_paw", paws=self.paws, paw_labels=self.paw_labels, paw_data=self.paw_data,
                        average_data=self.average_data, current_paw_index=self.current_paw_index)

    def calculate_average(self):
        # Empty average data
        self.average_data.clear()
        self.data_list.clear()
        # Group all the data per paw
        for measurement_name, data_list in self.paw_data.items():
            for index, data in enumerate(data_list):
                paw_label = self.paw_labels[measurement_name][index]
                if paw_label >= 0:
                    self.data_list[paw_label].append(data)

        # Then get the normalized data
        for paw_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data)
            self.average_data[paw_label] = normalized_data

    def calculate_results(self):
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()

        for paw_label, data_list in self.data_list.items():
            self.results[paw_label]["filtered"] = utility.filter_outliers(data_list, paw_label)
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

                cop_x, cop_y = calculations.calculate_cop(data, version="numpy")
                self.results[paw_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > self.max_results.get("duration", 0):
                    self.max_results["duration"] = max_duration

    def store_status(self):
        """
        This function creates a file in the store_results_folder and create the folder if it doesn't exist
        It will notify the status bar, log and return a boolean value depending on the success or failure of execution
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io.create_results_folder(self.dog_name)
        # Try storing the results
        try:
            io.results_to_json(self.new_path, self.dog_name, self.measurement_name,
                               self.paw_labels, self.paws, self.paw_data)
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
        self.paw_data.clear()
        self.paw_labels.clear()
        pub.sendMessage("clear_cached_values")