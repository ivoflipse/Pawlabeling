from collections import defaultdict
import logging
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
        # TODO change the models measurement folder instead of writing it to the settings
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()



        # Initialize our variables that will cache results
        self.subject_id = ""
        self.subject_name = ""
        self.session_id = ""
        self.session = {}
        self.sessions = []
        self.measurement_name = ""
        self.measurement = {}
        self.measurements = []
        self.contact = {}
        self.contacts = {}
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.max_results = defaultdict()
        self.n_max = 0

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


    def load_file_paths(self):
        self.logger.info("Model.load_file_paths: Loading file paths")
        self.file_paths = io.get_file_paths()
        pub.sendMessage("get_file_paths", file_paths=self.file_paths)

    def changed_settings(self):
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()

    def clear_cached_values(self):
        self.subject_id = ""
        self.subject_name = ""
        self.session_id = ""
        self.session.clear()
        self.sessions = []
        self.measurement_name = ""
        self.measurement.clear()
        self.measurements = []
        self.contact.clear()
        self.contacts.clear()
        self.average_data.clear()
        self.results.clear()
        self.max_results.clear()
        self.n_max = 0

        self.logger.info("Model.clear_cached_values")
        pub.sendMessage("clear_cached_values")
