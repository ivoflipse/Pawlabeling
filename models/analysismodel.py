import os
from collections import defaultdict
import numpy as np
from settings import configuration
from functions import io, tracking, utility, gui
from functions.pubsub import pub
import logging

class AnalysisModel():
    def __init__(self, parent):
        self.file_paths = defaultdict(dict)
        self.path = configuration.measurement_folder
        self.store_path = configuration.store_results_folder
        self.paw_dict = configuration.paw_dict

        self.dog_name = ""
        self.frame = 0
        self.n_max = 0

        # Initialize our variables that will cache results
        self.average_data = defaultdict()
        self.paw_data = defaultdict(list)
        self.paw_labels = defaultdict(dict)
        self.paws = defaultdict(list)
        self.data_list = defaultdict(list)

        self.logger = logging.getLogger("logger")

    def load_measurements(self):
        self.file_paths = io.load_measurements()
        return self.file_paths

