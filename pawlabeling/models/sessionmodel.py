import logging
from collections import defaultdict
import numpy as np
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.settings import settings
from pawlabeling.functions import calculations, utility


class SessionModel(object):
    def __init__(self, subject_id):
        self.subject_id = subject_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.sessions_table = table.SessionsTable(database_file=self.database_file, subject_id=subject_id)
        self.logger = logging.getLogger("logger")

    def create_session(self, session):
        # Check if the session isn't already in the table
        result = self.sessions_table.get_session(session_name=session["session_name"])
        if result:
            return result["session_id"]

        session_id = self.sessions_table.get_new_id()
        session["session_id"] = session_id
        self.session_group = self.sessions_table.create_session(**session)
        return session_id

    def get_sessions(self):
        sessions = self.sessions_table.get_sessions()
        return sessions

    # TODO see when this function is being called and make sure it doesn't happen unnecessarily
    def calculate_data_list(self, contacts):
        data_list = defaultdict(list)

        mx = 0
        my = 0
        mz = 0
        # Group all the measurement_data per contact
        for measurement_name, contacts in contacts.items():
            for contact in contacts:
                contact_label = contact.contact_label
                if contact_label >= 0:
                    data_list[contact_label].append(contact.data)

                x, y, z = contact.data.shape
                if x > mx:
                    mx = x
                if y > my:
                    my = y
                if z > mz:
                    mz = z

        shape = (mx, my, mz)
        return data_list, shape

    def calculate_average(self, data_list, shape):
        average_data = {}
        # Then get the normalized measurement_data
        for contact_label, data in data_list.items():
            normalized_data = utility.calculate_average_data(data, shape)
            average_data[contact_label] = normalized_data

        return average_data

    # TODO Why are we calculating stuff? These things are already stored, so be lazy and load them!
    def calculate_results(self, data_list, plate):
        # If we don't have any data, its no use to try and calculate something
        if len(data_list.keys()) == 0:
            return

        results = defaultdict(lambda: defaultdict(list))
        max_results = {}

        for contact_label, data in data_list.items():
            results[contact_label]["filtered"] = utility.filter_outliers(data, contact_label)
            for data in data:
                force = calculations.force_over_time(data)
                results[contact_label]["force"].append(force)
                max_force = np.max(force)
                if max_force > max_results.get("force", 0):
                    max_results["force"] = max_force

                pressure = calculations.pressure_over_time(data, sensor_surface=plate["sensor_surface"])
                results[contact_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > max_results.get("pressure", 0):
                    max_results["pressure"] = max_pressure

                surface = calculations.surface_over_time(data, sensor_surface=plate["sensor_surface"])
                results[contact_label]["surface"].append(surface)
                max_surface = np.max(surface)
                if max_surface > max_results.get("surface", 0):
                    max_results["surface"] = max_surface

                cop_x, cop_y = calculations.calculate_cop(data)
                results[contact_label]["cop"].append((cop_x, cop_y))

                x, y, z = np.nonzero(data)
                max_duration = np.max(z)
                if max_duration > max_results.get("duration", 0):
                    max_results["duration"] = max_duration

        return results, max_results