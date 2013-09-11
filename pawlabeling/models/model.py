from collections import defaultdict
import logging
import numpy as np
from pubsub import pub
from pawlabeling.functions import utility, io, tracking, calculations
from pawlabeling.settings import settings
from pawlabeling.models import table, subjectmodel, sessionmodel, measurementmodel, contactmodel, platemodel
#from memory_profiler import profile


class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.settings = settings.settings
        # TODO change the models measurement folder instead of writing it to the settings
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()

        self.plate_model = platemodel.PlateModel()
        self.plates = self.plate_model.get_plates()
        pub.sendMessage("update_plates", plates=self.plates)

        self.subject_model = subjectmodel.SubjectModel()

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
        # pub.subscribe(self.load_contacts, "load_contacts")
        # pub.subscribe(self.update_current_contact, "update_current_contact")
        # pub.subscribe(self.store_contacts, "store_contacts")
        # pub.subscribe(self.repeat_track_contacts, "track_contacts")
        # pub.subscribe(self.calculate_results, "calculate_results")
        # CREATE
        #pub.subscribe(self.create_subject, "create_subject")
        #pub.subscribe(self.create_session, "create_session")
        #pub.subscribe(self.create_measurement, "create_measurement")
        #pub.subscribe(self.create_contact, "create_contact")
        #pub.subscribe(self.create_plate, "create_plate")
        # GET
        # pub.subscribe(self.get_subjects, "get_subjects")
        # pub.subscribe(self.get_sessions, "get_sessions")
        # pub.subscribe(self.get_measurements, "get_measurements")
        # pub.subscribe(self.get_contacts, "get_contacts")
        # pub.subscribe(self.get_measurement_data, "get_measurement_data")
        # pub.subscribe(self.get_plates, "get_plates")
        # # PUT
        # pub.subscribe(self.put_subject, "put_subject")
        # pub.subscribe(self.put_session, "put_session")
        # pub.subscribe(self.put_measurement, "put_measurement")
        # pub.subscribe(self.put_contact, "put_contact")
        # pub.subscribe(self.put_plate, "put_plate")
        # Various
        pub.subscribe(self.changed_settings, "changed_settings")

    def create_subject(self, subject):
        self.subject_id = self.subject_model.create_subject(subject=subject)
        pub.sendMessage("update_statusbar", status="Model.create_subject: Subject created")

    def create_session(self, session):
        if not self.subject_id:
            pub.sendMessage("update_statusbar", status="Model.create_session: Subject not selected")
            pub.sendMessage("message_box", message="Please select a subject")
            raise settings.MissingIdentifier("Subject missing")

        self.session_model = sessionmodel.SessionModel(subject_id=self.subject_id)
        self.session_id = self.session_model.create_session(session=session)
        pub.sendMessage("update_statusbar", status="Model.create_session: Session created")

    def create_measurement(self, measurement):
        if not self.session_id:
            pub.sendMessage("update_statusbar", status="Model.create_measurement: Session not selected")
            pub.sendMessage("message_box", message="Please select a session")
            return

        self.measurement_model = measurementmodel.MeasurementModel(subject_id=self.subject_id,
                                                                   session_id=self.session_id)
        self.measurement_id = self.measurement_model.create_measurement(measurement=measurement, plates=self.plates)
        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement created")

        # TODO This part still feels rather messy...
        self.measurement_model.create_measurement_data()
        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement data created")

        self.contact_model = contactmodel.ContactModel(subject_id=self.subject_id,
                                                       session_id=self.session_id,
                                                       measurement_id=self.measurement_id)
        self.contact_model.create_contacts()

    def get_subjects(self):
        self.subjects = self.subject_model.get_subjects()
        pub.sendMessage("update_subjects_tree", subjects=self.subjects)

    def get_sessions(self):
        self.sessions = self.session_model.get_sessions()
        pub.sendMessage("update_sessions_tree", sessions=self.sessions)

    def get_measurements(self):
        self.measurements = self.measurement_model.get_measurements()
        pub.sendMessage("update_measurements_tree", measurements=self.measurements)

        # From one of the measurements, get its plate_id and call put_plate
        if self.measurements:
            # Update the plate information
            plate = self.plates[self.measurements[0]["plate_id"]]
            self.put_plate(plate)

    def get_contacts(self):
        self.contacts = self.contact_model.get_contacts(self.measurement_name)

        # TODO Why did I need this part again?
        # if not self.contacts.get(measurement_name):
        #     contacts = self.get_contact_data(self.measurement)
        #     if not contacts:
        #         self.contacts[self.measurement_name] = self.track_contacts()
        #     else:
        #         self.contacts[self.measurement_name] = contacts

        pub.sendMessage("update_contacts_tree", contacts=self.contacts)
        # Check if we should update n_max everywhere
        self.update_n_max()

    def get_measurement_data(self):
        self.measurement_data = self.measurement_model.get_measurement_data()
        pub.sendMessage("update_measurement_data", measurement_data=self.measurement_data)

    def update_n_max(self):
        self.n_max = self.measurement_model.update_n_max()
        pub.sendMessage("update_n_max", n_max=self.n_max)

    def put_plate(self, plate):
        self.plate = plate
        self.plate_id = plate["plate_id"]
        self.sensor_surface = self.plate["sensor_surface"]
        self.logger.info("Plate ID set to {}".format(self.plate_id))
        pub.sendMessage("update_plate", plate=self.plate)


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
