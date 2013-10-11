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

        self.plate_model = platemodel.Plates()
        # Create the plates if they do not yet exists
        self.plate_model.create_plates()

        self.subject_model = subjectmodel.Subjects()

        # Initialize our variables that will cache results
        self.subject_id = ""
        self.subject_name = ""
        self.session_id = ""
        self.session = {}
        self.sessions = {}
        self.measurement_name = ""
        self.measurement = {}
        self.measurements = {}
        self.contact = {}
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.selected_contacts = defaultdict()
        self.max_results = defaultdict()
        self.n_max = 0
        self.current_measurement_index = 0

        self.logger = logging.getLogger("logger")

        # CREATE
        pub.subscribe(self.create_subject, "create_subject")
        pub.subscribe(self.create_session, "create_session")
        pub.subscribe(self.create_measurement, "create_measurement")
        #pub.subscribe(self.create_contacts, "create_contact")
        #pub.subscribe(self.create_plate, "create_plate")
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
        # DELETE
        pub.subscribe(self.delete_subject, "delete_subject")
        pub.subscribe(self.delete_session, "delete_session")
        pub.subscribe(self.delete_measurement, "delete_measurement")
        # Various
        pub.subscribe(self.load_contacts, "load_contacts")
        pub.subscribe(self.update_current_contact, "update_current_contact")
        pub.subscribe(self.store_contacts, "store_contacts")
        pub.subscribe(self.repeat_track_contacts, "track_contacts")
        #pub.subscribe(self.calculate_results, "calculate_results")
        pub.subscribe(self.changed_settings, "changed_settings")

    def create_subject(self, subject):
        self.subject_id = self.subject_model.create_subject(subject=subject)
        pub.sendMessage("update_statusbar", status="Model.create_subject: Subject created")

    def create_session(self, session):
        if not self.subject_id:
            pub.sendMessage("update_statusbar", status="Model.create_session: Subject not selected")
            pub.sendMessage("message_box", message="Please select a subject")
            raise settings.MissingIdentifier("Subject missing")

        self.session_model = sessionmodel.Sessions(subject_id=self.subject_id)
        self.session_id = self.session_model.create_session(session=session)
        pub.sendMessage("update_statusbar", status="Model.create_session: Session created")

    def create_measurement(self, measurement):
        if not self.session_id:
            pub.sendMessage("update_statusbar", status="Model.create_measurement: Session not selected")
            pub.sendMessage("message_box", message="Please select a session")
            return

        self.measurement_model = measurementmodel.Measurements(subject_id=self.subject_id,
                                                               session_id=self.session_id)
        measurement = self.measurement_model.create_measurement(measurement=measurement, plates=self.plates)
        if not measurement:
            return

        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement created")
        measurement_data = measurement.measurement_data
        plate = measurement.plate

        self.create_measurement_data(measurement, measurement_data)
        self.create_contacts(measurement, measurement_data, plate)

    def create_measurement_data(self, measurement, measurement_data):
        self.measurement_model.create_measurement_data(measurement=measurement,
                                                       measurement_data=measurement_data)
        pub.sendMessage("update_statusbar", status="Model.create_measurement: Measurement data created")

    def create_contacts(self, measurement, measurement_data, plate):
        self.contact_model = contactmodel.Contacts(subject_id=self.subject_id,
                                                   session_id=self.session_id,
                                                   measurement_id=measurement.measurement_id)

        self.contacts[measurement.measurement_name] = self.contact_model.create_contacts(measurement=measurement,
                                                                                         measurement_data=measurement_data,
                                                                                         plate=plate)
        status = "Number of contacts found: {}".format(len(self.contacts[measurement.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)
        self.logger.info("model.create_contact: {}".format(status))

    def get_subjects(self):
        self.subjects = self.subject_model.get_subjects()
        pub.sendMessage("update_subjects_tree")

    def get_sessions(self):
        self.sessions = self.session_model.get_sessions()
        pub.sendMessage("update_sessions_tree")

    def get_measurements(self):
        self.measurements = self.measurement_model.get_measurements()
        pub.sendMessage("update_measurements_tree")

    def get_contacts(self):
        # self.contacts gets initialized when the session is loaded
        # if you want to track again, call repeat_track_contacts
        self.current_contact_index = 0
        pub.sendMessage("update_contacts")

    def get_measurement_data(self):
        self.measurement_data = self.measurement_model.get_measurement_data(self.measurement)
        pub.sendMessage("update_measurement_data")

    def get_plates(self):
        self.plates = self.plate_model.get_plates()
        pub.sendMessage("update_plates")

    def get_plate(self):
        # From one of the measurements, get its plate_id and call put_plate
        if self.measurements:
            plate = None
            for measurement_id, measurement in self.measurements.iteritems():
                # Update the plate information
                plate = self.plates[measurement.plate_id]

            self.put_plate(plate)
            return plate

    def put_subject(self, subject):
        self.subject = subject
        self.subject_id = subject.subject_id
        self.logger.info("Subject ID set to {}".format(self.subject_id))
        # As soon as a subject is selected, we instantiate our sessions table
        self.sessions_table = table.SessionsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id)
        self.session_model = sessionmodel.Sessions(subject_id=self.subject_id)
        pub.sendMessage("update_statusbar", status="Subject: {} {}".format(self.subject.first_name,
                                                                           self.subject.last_name))
        self.subject_name = "{} {}".format(self.subject.first_name, self.subject.last_name)
        self.get_sessions()

    def put_session(self, session):
        self.clear_cached_values()
        self.session = session
        self.session_id = session.session_id
        self.logger.info("Session ID set to {}".format(self.session_id))
        pub.sendMessage("update_statusbar", status="Session: {}".format(self.session.session_name))

        self.measurements_table = table.MeasurementsTable(database_file=self.database_file,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)
        self.measurement_model = measurementmodel.Measurements(subject_id=self.subject_id,
                                                               session_id=self.session_id)

        # TODO How did I manage to keep making this stuff so complicated?!?
        # TODO perhaps I should roll these below functions into one, then call get_blabla on the results later

        # Load all the measurements for this session
        self.get_measurements()
        # If there are no measurements yet, stop right here
        if not self.measurements:
            return

        # Create Contacts instances for each measurement
        self.contact_models = {}
        for measurement in self.measurements.values():
            contact_model = contactmodel.Contacts(subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=measurement.measurement_id)
            self.contact_models[measurement.measurement_name] = contact_model

        self.get_plate()
        # Load the contacts, but have it not send out anything
        self.load_contacts()
        self.update_n_max()
        self.update_average()

    # TODO This function is messed up again!
    def put_measurement(self, measurement_name):
        for measurement in self.measurements.values():
            if measurement.measurement_name == measurement_name:
                self.measurement = measurement
                self.measurement_id = measurement.measurement_id
                self.measurement_name = measurement.measurement_name
                break

        self.logger.info("Measurement ID set to {}".format(self.measurement_id))
        self.contacts_table = table.ContactsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)
        self.contact_model = self.contact_models[measurement.measurement_name]
        pub.sendMessage("update_statusbar", status="Measurement: {}".format(self.measurement_name))
        pub.sendMessage("update_measurement")

        # TODO Have this load the contacts and measurement data
        # Now get everything that belongs to the measurement, the contacts and the measurement_data
        self.get_measurement_data()
        # Check that its not empty
        assert self.contacts[self.measurement_name]
        # TODO get_contacts doesn't really do anything, but send a message, can't this be done differently
        self.get_contacts()

    # TODO What happens if you select a contact from another measurement?
    def put_contact(self, contact_id):
        # Find the contact with the corresponding id
        for contact in self.contacts[self.measurement_name]:
            if contact.contact_id == contact_id:
                self.contact = contact
                self.contact_id = self.contact.contact_id
                self.logger.info("Contact ID set to {}".format(self.contact_id))
                self.selected_contacts[self.contact.contact_label] = contact
                pub.sendMessage("update_contact")
                break

    def put_plate(self, plate):
        self.plate = plate
        self.plate_id = plate.plate_id
        self.sensor_surface = self.plate.sensor_surface
        self.logger.info("Plate ID set to {}".format(self.plate_id))
        # TODO I doubt anyone even cares about this message any more
        pub.sendMessage("update_plate")

    def delete_subject(self, subject):
        self.subject_model.delete_subject(subject)
        # Have all widgets refresh their view of the subjects by calling get_subjects
        self.get_subjects()

    def delete_session(self, session):
        self.session_model.delete_session(session)
        # Have all widgets refresh their view of the subjects by calling get_sessions
        self.get_sessions()

    def delete_measurement(self, measurement):
        self.measurement_model.delete_measurement(measurement)
        self.get_measurements()

    def update_current_contact(self):
        # Notify everyone things have been updated
        self.update_average()
        pub.sendMessage("updated_current_contact")

    def store_contacts(self):
        self.contact_model.update_contacts(contacts=self.contacts, measurement_name=self.measurement_name)
        self.logger.info("Model.update_contacts: Results for {} have been successfully saved".format(
            self.measurement_name))
        pub.sendMessage("update_statusbar", status="Results saved")
        pub.sendMessage("stored_status", success=True)
        # Notify the measurement that it has been processed
        self.measurement.processed = True
        self.measurement_model.update(measurement=self.measurement)

    def reset_contact_labels(self):
        for contact in self.contacts[self.measurement_name]:
            contact.contact_label = -2

        pub.sendMessage("update_contacts_tree")

    # TODO This should only be used when you've changed tracking thresholds
    def repeat_track_contacts(self):
        contacts = self.contact_model.repeat_track_contacts(measurement=self.measurement,
                                                            measurement_data=self.measurement_data,
                                                            plate=self.plate)
        self.contacts[self.measurement_name] = contacts
        pub.sendMessage("update_contacts_tree")

    # TODO Make sure this function doesn't have to pass along data
    def load_contacts(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        self.logger.info("Model.load_contacts: Loading all measurements for subject: {}, session: {}".format(
            self.subject_name, self.session.session_name))
        self.contacts.clear()

        measurements = {}
        for measurement_id, measurement in self.measurements.iteritems():
            contact_model = self.contact_models[measurement.measurement_name]
            contacts = contact_model.get_contacts(measurement)
            if contacts:
                self.contacts[measurement.measurement_name] = contacts

            if not all([True if contact.contact_label < 0 else False for contact in contacts]):
                measurements[measurement.measurement_name] = measurement

        # This notifies the measurement_trees which measurements have contacts assigned to them
        pub.sendMessage("update_measurement_status")


    def update_average(self):
        self.shape = self.session_model.calculate_shape(contacts=self.contacts)
        self.average_data = self.session_model.calculate_average_data(contacts=self.contacts,
                                                                      shape=self.shape)
        pub.sendMessage("update_average")

    def calculate_results(self):
        self.update_average()
        # This updates contacts in place
        self.session_model.calculate_results(contacts=self.contacts)
        # This might have changed self.contacts, so we should update it to be sure
        for measurement_name, contacts in self.contacts.items():
            # Make sure to update on the right model
            contact_model = self.contact_models[measurement_name]
            contact_model.update_contacts(measurement_name=measurement_name, contacts=self.contacts)

    def update_n_max(self):
        self.n_max = self.measurement_model.update_n_max()
        pub.sendMessage("update_n_max")

    def changed_settings(self):
        self.measurement_folder = self.settings.measurement_folder()
        self.database_file = self.settings.database_file()

    def clear_cached_values(self):
        # TODO Figure out what can be cleared and when, perhaps I can use an argument to check the level of clearing
        # like, subject/session/measurement etc
        #print "model.clear_cached_values"
        #self.subject_id = ""
        #self.subject_name = ""
        #self.session_id = ""
        #self.session.clear()
        #self.sessions = {}
        self.measurement_name = ""
        # self.measurement.clear()
        self.measurements = {}
        self.contact.clear()
        self.contacts.clear()
        self.average_data.clear()
        self.results.clear()
        self.max_results.clear()
        self.n_max = 0

        self.logger.info("Model.clear_cached_values")
        pub.sendMessage("clear_cached_values")


model = Model()