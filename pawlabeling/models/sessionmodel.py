import logging
from collections import defaultdict
import numpy as np
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.settings import settings
from pawlabeling.functions import calculations, utility


class Sessions(object):
    def __init__(self, subject_id):
        self.subject_id = subject_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.sessions_table = table.SessionsTable(database_file=self.database_file, subject_id=subject_id)
        self.logger = logging.getLogger("logger")

    def create_session(self, session):
        session_object = Session(self.subject_id)
        # Check if the session isn't already in the table
        if self.sessions_table.get_session(session_name=session["session_name"]):
            return

        session_id = self.sessions_table.get_new_id()
        session_object.create_session(session_id=session_id, session=session)
        session = session_object.to_dict()
        self.session_group = self.sessions_table.create_session(**session)
        return session_object

    def delete_session(self, session):
        # Delete both the row and the group
        self.sessions_table.remove_row(table=self.sessions_table.sessions_table,
                                       name_id="session_id",
                                       item_id=session.session_id)
        self.sessions_table.remove_group(where="/{}".format(self.subject_id),
                                         name=session.session_id)

    def get_sessions(self):
        sessions = {}
        for session in self.sessions_table.get_sessions():
            session_object = Session(self.subject_id)
            session_object.restore(session)
            sessions[session_object.session_id] = session_object
        return sessions

    def update_average(self, contacts, shape):
        average_data = self.calculate_average_data(contacts=contacts, shape=shape)
        return average_data

    def calculate_shape(self, contacts):
        mx = 0
        my = 0
        mz = 0

        # Iterate over the contacts and retrieve the overall size
        for measurement_name, contacts in contacts.iteritems():
            for contact in contacts:
                x, y, z = contact.data.shape
                if x > mx:
                    mx = x
                if y > my:
                    my = y
                if z > mz:
                    mz = z

        # We need to add some padding for the interpolation of the views
        mx += 4
        my += 4
        return mx, my, mz

    # TODO see when this function is being called and make sure it doesn't happen unnecessarily
    # TODO perhaps I should even include -1, so I automatically get the correctly shaped current_contact
    def calculate_average_data(self, contacts, shape):
        num_contacts = defaultdict(int)
        mx, my, mz = shape
        average_data = {}
        for measurement_name, contacts in contacts.iteritems():
            for contact in contacts:
                if contact.contact_label >= 0:
                    num_contacts[contact.contact_label] += 1
                    x, y, z = contact.data.shape
                    offset_x = int((mx - x) / 2)
                    offset_y = int((my - y) / 2)
                    # Check if the contact_label is present, else initialize with an empty array
                    if contact.contact_label not in average_data:
                        average_data[contact.contact_label] = np.zeros(shape)

                    data = average_data[contact.contact_label]
                    data[offset_x:offset_x + x, offset_y:offset_y + y, :z] += contact.data

        for contact_label, data in average_data.iteritems():
            if num_contacts[contact_label] > 0:
                weight = 1. / num_contacts[contact_label]
                average_data[contact_label] = np.multiply(data, weight)

        return average_data

    # TODO Why are we calculating stuff? These things are already stored, so be lazy and load them!
    def calculate_results(self, contacts, plate):
        results = defaultdict(lambda: defaultdict(list))
        max_results = {}

        for contact_label, contact in contacts.iteritems():
            data = contact.data
            results[contact_label]["filtered"] = utility.filter_outliers(data, contact_label)
            for data in data:
                force = calculations.force_over_time(data)
                results[contact_label]["force"].append(force)
                max_force = np.max(force)
                if max_force > max_results.get("force", 0):
                    max_results["force"] = max_force

                pressure = calculations.pressure_over_time(data, sensor_surface=plate.sensor_surface)
                results[contact_label]["pressure"].append(pressure)
                max_pressure = np.max(pressure)
                if max_pressure > max_results.get("pressure", 0):
                    max_results["pressure"] = max_pressure

                surface = calculations.surface_over_time(data, sensor_surface=plate.sensor_surface)
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

    def create_session_data(self, average_contact):
        # Get the label we're dealing with
        contact_label = average_contact.contact_label

        results = {"data": average_contact.data,
                   "max_of_max": average_contact.max_of_max,
                   "force_over_time": average_contact.force_over_time,
                   "pressure_over_time": average_contact.pressure_over_time,
                   "surface_over_time": average_contact.surface_over_time,
                   "cop_x": average_contact.cop_x,
                   "cop_y": average_contact.cop_y
        }

        # Check if the group for this contact_label exists, else create it
        if hasattr(self.session_group.contacts, contact_label):
            self.contact_group = self.session_group.contacts.__getattr__(contact_label)
        else:
            self.contact_group = self.sessions_table.create_group(parent=self.session_group, item_id=contact_label)

        for item_id, data in results.iteritems():
            result = self.sessions_table.get_data(group=self.contact_group, item_id=item_id)
            if not result:
                self.sessions_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)
            elif not np.array_equal(result, data):
                print "Stored session data is not equal to new data"
                self.sessions_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)


class Session(object):
    """
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        session_name = tables.StringCol(32)
        session_date = tables.StringCol(32)
        session_time = tables.StringCol(32)
    """

    def __init__(self, subject_id):
        self.subject_id = subject_id

    def create_session(self, session_id, session):
        self.session_id = session_id
        self.session_name = session["session_name"]
        self.session_date = session["session_date"]
        self.session_time = session["session_time"]

    def to_dict(self):
        session = {
            "subject_id": self.subject_id,
            "session_name": self.session_name,
            "session_id": self.session_id,
            "session_date": self.session_date,
            "session_time": self.session_time
        }
        return session

    def restore(self, session):
        self.subject_id = session["subject_id"]
        self.session_id = session["session_id"]
        self.session_name = session["session_name"]
        self.session_date = session["session_date"]
        self.session_time = session["session_time"]