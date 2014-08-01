from collections import defaultdict
#import numpy as np
import pandas as pd
from pubsub import pub
#from ..functions import utility, io, tracking, calculations
from ..settings import settings
from ..models import table, subjectmodel, sessionmodel, measurementmodel, contactmodel, platemodel
#from memory_profiler import profile


class Model():
    def __init__(self):
        self.file_paths = defaultdict(dict)
        self.measurement_folder = settings.settings.measurement_folder()
        self.table = settings.settings.table
        self.plate_model = platemodel.Plates()
        # Create the plates if they do not yet exists
        self.plate_model.create_plates()

        self.subject_model = subjectmodel.Subjects()
        # Initialize our variables that will cache results
        self.subject_id = ""
        self.subject_name = ""
        self.session_id = ""
        self.session = None
        self.sessions = {}
        self.measurement_name = ""
        self.measurement = None
        self.measurements = {}
        self.contact = None
        self.average_data = defaultdict()
        self.contacts = defaultdict(list)
        self.results = defaultdict(lambda: defaultdict(list))
        self.selected_contacts = defaultdict()
        self.max_results = defaultdict()
        self.n_max = 0
        self.current_measurement_index = 0
        self.outlier_toggle = False

        # Various
        pub.subscribe(self.changed_settings, "changed_settings")
        pub.subscribe(self.filter_outliers, "filter_outliers")

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

        contacts = self.contact_model.track_contacts(measurement=measurement,
                                                     measurement_data=measurement_data,
                                                     plate=plate)
        self.contact_model.create_contacts(contacts)
        self.contacts[measurement.measurement_name] = contacts
        status = "Number of contacts found: {}".format(len(self.contacts[measurement.measurement_name]))
        pub.sendMessage("update_statusbar", status=status)
        settings.settings.logger.info("model.create_contact: {}".format(status))

    def get_subjects(self):
        self.subjects = self.subject_model.get_subjects()
        pub.sendMessage("get_subjects")

    def get_sessions(self):
        self.sessions = self.session_model.get_sessions()
        pub.sendMessage("get_sessions")

    def get_measurements(self):
        self.measurements = self.measurement_model.get_measurements()
        pub.sendMessage("get_measurements")

    def get_contacts(self):
        # self.contacts gets initialized when the session is loaded
        # if you want to track again, call repeat_track_contacts
        self.current_contact_index = 0
        pub.sendMessage("get_contacts")

    def get_measurement_data(self):
        self.measurement_data = self.measurement_model.get_measurement_data(self.measurement)
        # TODO damn, I'm triggering events from the wrong place again...
        pub.sendMessage("get_measurement_data")

    def get_plates(self):
        self.plates = self.plate_model.get_plates()
        pub.sendMessage("get_plates")

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
        settings.settings.logger.info("Subject ID set to {}".format(self.subject_id))
        # As soon as a subject is selected, we instantiate our sessions table
        self.sessions_table = table.SessionsTable(table=self.table,
                                                  subject_id=self.subject_id)
        self.session_model = sessionmodel.Sessions(subject_id=self.subject_id)
        pub.sendMessage("update_statusbar", status="Subject: {} {}".format(self.subject.first_name,
                                                                           self.subject.last_name))
        self.subject_name = "{} {}".format(self.subject.first_name, self.subject.last_name)
        pub.sendMessage("put_subject")
        self.get_sessions()

    def put_session(self, session):
        self.clear_cached_values()
        self.session = session
        self.session_id = session.session_id
        settings.settings.logger.info("Session ID set to {}".format(self.session_id))
        pub.sendMessage("update_statusbar", status="Session: {}".format(self.session.session_name))

        self.measurements_table = table.MeasurementsTable(table=self.table,
                                                          subject_id=self.subject_id,
                                                          session_id=self.session_id)
        self.measurement_model = measurementmodel.Measurements(subject_id=self.subject_id,
                                                               session_id=self.session_id)
        pub.sendMessage("put_session")

        # TODO How did I manage to keep making this stuff so complicated?!?
        # TODO perhaps I should roll these below functions into one, then call get_blabla on the results later

        pub.sendMessage("update_progress", progress=0)
        # Load all the measurements for this session
        self.get_measurements()
        # If there are no measurements yet, stop right here
        if not self.measurements:
            return

        pub.sendMessage("update_progress", progress=50)
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
        pub.sendMessage("update_progress", progress=75)
        self.update_n_max()
        # Pray this doesn't have side-effects
        self.calculate_results()
        pub.sendMessage("update_progress", progress=100)


    # TODO This function is messed up again!
    def put_measurement(self, measurement_id):
        measurement = self.measurements[measurement_id]
        self.measurement = measurement
        self.measurement_id = measurement.measurement_id
        self.measurement_name = measurement.measurement_name

        settings.settings.logger.info("Measurement ID set to {}".format(self.measurement_id))
        self.contact_model = self.contact_models[measurement.measurement_name]
        pub.sendMessage("update_statusbar", status="Measurement: {}".format(self.measurement_name))
        pub.sendMessage("put_measurement")

        # TODO Have this load the contacts and measurement data
        # Now get everything that belongs to the measurement, the contacts and the measurement_data
        self.get_measurement_data()
        # TODO I turned off the assertion, though I'm intrigued by how its possible
        # Check that its not empty
        #assert self.contacts[self.measurement_name]
        # TODO get_contacts doesn't really do anything, but send a message, can't this be done differently?
        self.get_contacts()

    def put_contact(self, contact_id):
        # Find the contact with the corresponding id
        for contact in self.contacts[self.measurement_name]:
            if contact.contact_id == contact_id:
                self.contact = contact
                self.contact_id = self.contact.contact_id
                settings.settings.logger.info("Contact ID set to {}".format(self.contact_id))
                self.selected_contacts[self.contact.contact_label] = contact
                pub.sendMessage("put_contact")
                break

    def put_plate(self, plate):
        self.plate = plate
        self.plate_id = plate.plate_id
        self.sensor_surface = self.plate.sensor_surface
        settings.settings.logger.info("Plate ID set to {}".format(self.plate_id))

    def delete_subject(self, subject):
        self.subject_model.delete_subject(subject)
        # Have all widgets refresh their trees, they might be empty
        self.get_subjects()
        self.get_sessions()
        self.get_measurements()

    def delete_session(self, session):
        self.session_model.delete_session(session)
        # Have all widgets refresh their view of the subjects by calling get_sessions
        self.get_sessions()
        self.get_measurements()

    def delete_measurement(self, measurement):
        self.measurement_model.delete_measurement(measurement)
        self.get_measurements()

    def update_current_contact(self):
        # Notify everyone things have been updated
        self.update_average()
        pub.sendMessage("update_current_contact")

    def filter_outliers(self, toggle):
        """
        This function tries to select a contact that's not filtered or invalid
        """
        self.outlier_toggle = toggle

        for contact_label, current_contact in self.selected_contacts.items():
            if not current_contact.filtered and not current_contact.invalid:
                continue
            for contact in self.contacts[self.measurement_name]:
                if contact.contact_label == contact_label and not contact.filtered and not contact.invalid:
                    self.selected_contacts[contact_label] = contact
                    self.put_contact(contact.contact_id)
                    break


    # TODO Store every contact, from every measurement?
    def store_contacts(self):
        measurement_data = self.measurement_model.get_measurement_data(self.measurement)
        # Make sure the results are up to date
        self.contact_model.recalculate_results(self.contacts[self.measurement_name],
                                               self.plate,
                                               self.measurement,
                                               measurement_data)
        self.contact_model.create_contacts(contacts=self.contacts[self.measurement_name])
        settings.settings.logger.info("Model.store_contacts: Results for {} have been successfully saved".format(
            self.measurement_name))
        pub.sendMessage("update_statusbar", status="Results saved")
        # Notify the measurement that it has been processed
        self.measurement.processed = True
        self.measurement_model.update(measurement=self.measurement)
        pub.sendMessage("update_measurement_status")

    # TODO This should only be used when you've changed tracking thresholds
    # Else it makes no sense at all
    def repeat_track_contacts(self):
        contacts = self.contact_model.repeat_track_contacts(measurement=self.measurement,
                                                            measurement_data=self.measurement_data,
                                                            plate=self.plate)
        self.contacts[self.measurement_name] = contacts
        # This notifies the other widgets that the contacts have been retrieved again
        self.get_contacts()

    # TODO Make sure this function doesn't have to pass along data
    def load_contacts(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        settings.settings.logger.info("Model.load_contacts: Loading all measurements for subject: {}, session: {}".format(
            self.subject_name, self.session.session_name))
        self.contacts.clear()

        measurements = {}
        for measurement_id, measurement in self.measurements.iteritems():
            contact_model = self.contact_models[measurement.measurement_name]
            plate = self.plates[measurement.plate_id]
            contacts = contact_model.get_contacts(plate, measurement)
            if contact_model.verify_contacts(contacts):
                measurement_data = self.measurement_model.get_measurement_data(measurement)
                contact_model.recalculate_results(contacts, plate, measurement, measurement_data)
                # Given the stored data is dirty, store it
                contact_model.create_contacts(contacts)

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
        self.max_length = self.shape[2]
        # Also calculate the length of only the filtered contacts
        self.filtered_length = 0
        for measurement_id, contacts in self.contacts.items():
            for contact in contacts:
                if not contact.filtered and not contact.invalid and contact.length > self.filtered_length:
                    self.filtered_length = contact.length
        pub.sendMessage("update_average")

    def calculate_results(self):
        self.update_average()
        # This updates contacts in place
        self.session_model.calculate_results(contacts=self.contacts)
        results = []
        for measurement_id, contacts in self.contacts.items():
            for contact in contacts:
                row = [measurement_id, contact.contact_id, contact.contact_label, contact.invalid, contact.filtered,
                       contact.peak_force, contact.peak_pressure, contact.peak_surface, contact.vertical_impulse,
                       contact.stance_duration, contact.stance_percentage, contact.step_duration, contact.step_length]
                results.append(row)

        self.dataframe = pd.DataFrame(results, columns=["measurement_id","contact_id","contact_label","invalid", "filtered",
                                                        "peak_force","peak_pressure","peak_surface","vertical_impulse",
                                                        "stance_duration","stance_percentage","step_duration","step_length",
       ])


    def update_n_max(self):
        self.n_max = self.measurement_model.update_n_max()
        pub.sendMessage("update_n_max")

    def changed_settings(self):
        self.measurement_folder = settings.settings.measurement_folder()

    def clear_cached_values(self):
        # TODO Figure out what can be cleared and when, perhaps I can use an argument to check the level of clearing
        # like, subject/session/measurement etc
        #print "model.clear_cached_values"
        self.measurement_name = ""
        self.measurements = {}
        self.contact = None
        self.contacts.clear()
        self.selected_contacts.clear()
        self.average_data.clear()
        self.results.clear()
        self.max_results.clear()
        self.n_max = 0

        settings.settings.logger.info("Model.clear_cached_values")
        pub.sendMessage("clear_cached_values")


model = Model()