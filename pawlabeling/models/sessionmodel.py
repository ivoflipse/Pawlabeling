import logging
from collections import defaultdict
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.settings import settings
from pawlabeling.functions import calculations


class SessionModel(object):
    def __init__(self, subject_id):
        self.subject_id = subject_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.sessions_table = table.SessionsTable(database_file=self.database_file, subject_id=subject_id)
        self.logger = logging.getLogger("logger")
        pub.subscribe(self.create_session, "create_session")

    def create_session(self, session):
        if not self.subject_id:
            pub.sendMessage("update_statusbar", status="Model.create_session: Subject not selected")
            pub.sendMessage("message_box", message="Please select a subject")
            raise settings.MissingIdentifier("Subject missing")

        # Check if the session isn't already in the table
        if self.sessions_table.get_session_row(session_name=session["session_name"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_session: Session already exists")
            return

        # How many sessions do we already have?
        session_id = self.sessions_table.get_new_id()
        session["session_id"] = session_id

        self.session_group = self.sessions_table.create_session(**session)
        pub.sendMessage("update_statusbar", status="Model.create_session: Session created")

    def get_sessions(self, session={}):
        self.sessions = self.sessions_table.get_sessions(**session)
        pub.sendMessage("update_sessions_tree", sessions=self.sessions)

    def put_session(self, session):
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

    def load_contacts(self):
        """
        Check if there if any measurements for this subject have already been processed
        If so, retrieve the measurement_data and convert them to a usable format
        """
        self.logger.info("Model.load_contacts: Loading all measurements for subject: {}, session: {}".format(
            self.subject_name, self.session["session_name"]))

        # Make sure self.contacts is empty
        self.contacts.clear()

        measurements = {}
        for measurement in self.measurements_table.measurements_table:
            contacts = self.get_contact_data(measurement)
            if contacts:
                self.contacts[measurement["measurement_name"]] = contacts

            if not all([True if contact.contact_label < 0 else False for contact in contacts]):
                measurements[measurement["measurement_name"]] = measurement

        pub.sendMessage("update_measurement_status", measurements=measurements)

    # TODO see when this function is being called and make sure it doesn't happen unnecessarily
    def calculate_average(self):
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
        pub.sendMessage("update_shape", shape=shape)
        # Then get the normalized measurement_data
        for contact_label, data in self.data_list.items():
            normalized_data = utility.calculate_average_data(data, shape)
            self.average_data[contact_label] = normalized_data

        pub.sendMessage("update_average", average_data=self.average_data)

        # TODO Why are we calculating stuff? These things are already stored, so be lazy and load them!
    def calculate_results(self):
        # If we don't have any data, its no use to try and calculate something
        if len(self.data_list.keys()) == 0:
            return

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

                pressure = calculations.pressure_over_time(data, sensor_surface=self.sensor_surface)
                self.results[contact_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > self.max_results.get("pressure", 0):
                    self.max_results["pressure"] = max_pressure

                surface = calculations.surface_over_time(data, sensor_surface=self.sensor_surface)
                self.results[contact_label]["surface"].append(surface)
                max_surface = np.max(surface)
                if max_surface > self.max_results.get("surface", 0):
                    self.max_results["surface"] = max_surface

                cop_x, cop_y = calculations.calculate_cop(data)
                self.results[contact_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > self.max_results.get("duration", 0):
                    self.max_results["duration"] = max_duration

        pub.sendMessage("update_results", results=self.results, max_results=self.max_results)