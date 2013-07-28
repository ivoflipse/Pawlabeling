import os
from collections import defaultdict
import numpy as np
from settings import configuration
from functions import io, tracking, utility, gui
from functions.pubsub import pub
import logging


class ProcessingModel():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder

        self.dog_name = ""

        # Initialize our variables that will cache results
        self.average_data = defaultdict(list)
        self.paw_data = defaultdict(list)
        self.paw_labels = defaultdict(dict)
        self.paws = defaultdict(list)

        self.logger = logging.getLogger("logger")

    def zip_files(self, root, file_name):
        # Check if the file isn't compressed, else zip it and delete the original after loading
        base_name, extension = os.path.splitext(file_name)
        if extension != ".zip":
            file_path = os.path.join(root, file_name)
            file_name = io.convert_file_to_zip(file_path)

        return os.path.join(root, file_name)

    def load_measurements(self):
        # Clear any existing file names
        self.file_paths.clear()

        self.logger.info("load_measurements: Searching for measurements...")
        # Walk through the folder and gather up all the files
        for idx, (root, dirs, files) in enumerate(os.walk(self.path)):
            if not dirs:
                # Add the name of the dog
                dog_name = root.split("\\")[-1]
                for index, file_name in enumerate(files):
                    # zip_files will convert a file to zip and returns the path to the file
                    self.file_paths[dog_name][file_name] = self.zip_files(root, file_name)

        return self.file_paths

    def switch_dogs(self, dog_name):
        """
        This function should always be called when you want to access other dog's results
        """
        self.logger.info("switch_dogs: Switching dogs from {} to {}".format(self.dog_name, dog_name))
        self.dog_name = dog_name

    def switch_measurements(self, measurement_name):
        self.logger.info(
            "switch_measurements: Switching measurements from {} to {}".format(self.measurement_name, measurement_name))
        self.measurement_name = measurement_name


    def load_file(self, measurement_name):
        # Get the path from the file_paths dictionary
        self.file_path = self.file_paths[self.dog_name][measurement_name]

        # Log which measurement we're loading
        self.logger.info("load_file: Loading measurement for dog: {} - {}".format(self.dog_name, measurement_name))

        # Pass the new measurement through to the widget
        data = io.load(self.file_path)

        x, y, z = data.shape
        self.measurement = np.zeros((x + 2, y + 2, z), np.float32)
        self.measurement[1:-1, 1:-1, :] = data

        # Check the orientation of the plate and make sure its left to right
        self.measurement = io.fix_orientation(self.measurement)
        # Get the number of frames for the slider
        self.height, self.width, self.num_frames = self.measurement.shape
        # Get the normalizing factor for the color bars
        self.n_max = self.measurement.max()

    def load_all_results(self):
        """
        Check if there if any measurements for this dog have already been processed
        If so, retrieve the data and convert them to a usable format
        """
        # Clear the average data
        self.average_data.clear()

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
                        # And don't forget to send an update. Though this would only have to happen once
                        self.paws_widget.update_n_max(self.n_max)

                    paw = utility.Contact(stored_results["paw_results"][index], restoring=True)
                    self.paws[measurement_name].append(paw)

                # Until I've moved everything to be dictionary based, here's code to sort the paws + paw_data
                # Fancy pants code found here:
                # http://stackoverflow.com/questions/9764298/is-it-possible-to-sort-two-listswhich-reference-each-other-in-the-exact-same-w
                self.paws[measurement_name], self.paw_data[measurement_name] = zip(*sorted(
                    zip(self.paws[measurement_name], self.paw_data[measurement_name]),
                    key=lambda pair: pair[0].frames[0]))

                for index, data in enumerate(self.paw_data[measurement_name]):
                    paw_label = self.paw_labels[measurement_name][index]
                    if paw_label >= 0:
                        normalized_data = utility.normalize_paw_data(data)
                        self.average_data[paw_label].append(normalized_data)

    def track_contacts(self):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        paws = tracking.track_contours_graph(self.measurement)

        # Make sure we don't have any paws stored if we're tracking again
        # TODO How do I know average_data isn't contaminated now?
        # I'd suggest moving the calculation of average_data out, so I can update it every time I label a paw
        self.paws[self.measurement_name] = []
        self.paw_labels[self.measurement_name] = {}
        self.paw_data[self.measurement_name] = []

        # Convert them to class objects
        for index, paw in enumerate(paws):
            paw = utility.Contact(paw)
            # Skip paws that have only been around for one frame
            if len(paw.frames) > 1:
                self.paws[self.measurement_name].append(paw)

        # TODO Somewhere in here, fix the padding, so its gone

        # Sort the contacts based on their position along the first dimension
        self.paws[self.measurement_name] = sorted(self.paws[self.measurement_name], key=lambda paw: paw.frames[0])

        for index, paw in enumerate(self.paws[self.measurement_name]):
            data_slice = utility.convert_contour_to_slice(self.measurement, paw.contour_list)
            self.paw_data[self.measurement_name].append(data_slice)
            # I've made -2 the label for unlabeled paws, -1 == unlabeled + selected
            paw_label = -2
            # Test if the paw touches the edge of the plate
            if utility.touches_edges(self.measurement, paw, padding=True):
                paw_label = -3  # Mark it as invalid
            elif utility.incomplete_step(data_slice):
                paw_label = -3
            self.paw_labels[self.measurement_name][index] = paw_label

        status = "Number of paws found: {}".format(len(self.paws[self.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)

    def store_status(self):
        """
        This function creates a file in the store_results_folder folder if it doesn't exist
        """
        # Try and create a folder to add store the store_results_folder result
        self.new_path = io.create_results_folder(self.dog_name)
        # Try storing the results
        try:
            io.results_to_json(self.new_path, self.dog_name, self.measurement_name,
                               self.paw_labels, self.paws, self.paw_data)
            self.logger.info("Results for {} have been successfully saved".format(self.measurement_name))
            pub.sendMessage("update_statusbar", status="Results saved")
        except Exception as e:
            self.logger.critical("Storing failed! {}".format(e))
            pub.sendMessage("update_statusbar", status="Storing results failed!")


    def clear_cached_values(self):
        self.average_data.clear()
        self.paws.clear()
        self.paw_data.clear()
        self.paw_labels.clear()