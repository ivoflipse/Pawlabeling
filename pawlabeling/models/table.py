from collections import defaultdict
import tables
from tables.exceptions import ClosedNodeError, NoSuchNodeError, NodeError

class MissingIdentifier(Exception):
    pass

# I should add some helper function to check if something can be found, if not raise an exception or log something
class Table(object):
    def __init__(self, table):
        # The settings has a table connection, we just create a copy of that
        # So not every subclass of this Table class will create its own copy
        self.table = table
        self.table_name = "table"
        self.filters = tables.Filters(complib="blosc", complevel=9)
        self.table.filters = self.filters

    def create_row(self, table, **kwargs):
        row = table.row

        for attr, value in kwargs.items():
            row[attr] = value

        # Append the row to the table
        row.append()
        # Flush the changes
        table.flush()

    def check_availability(self, table, column_name, value):
        for row in table:
            if row[column_name] == value[column_name]:
                raise AssertionError("Value in {} {} already taken!".format(table, column_name))

    def create_group(self, parent, item_id):
        # If the group already exists, delete it
        try:
            group = self.table.create_group(where=parent, name=item_id)
        except:
            self.table.remove_node(where=parent, name=item_id, recursive=True)
            group = self.table.create_group(where=parent, name=item_id)
        self.table.flush()
        return group

    def search_table(self, table, **kwargs):
        # Create a query out of the kwargs
        query = " & ".join(
            ["({} == '{}')".format(key, value) for key, value in kwargs.items() if value != ""])
        rows = table.read_where(query)

        results = []
        for row in rows:
            result = defaultdict()
            for key, value in zip(table.colnames, row):
                result[key] = value
            results.append(result)

        # It can happen that there's nothing to return
        if not results:
            return results  # This returns the empty list

        # Return a singular value if there's only one row
        return results if len(results) > 1 else results[0]

    # This function can be used for measurement_data, contact_data and normalized_contact_data
    # Actually also for all the different results (at least the time series)
    def store_data(self, group, item_id, data):
        atom = tables.Atom.from_dtype(data.dtype)
        filters = tables.Filters(complib="blosc", complevel=9)
        data_array = self.table.create_carray(where=group, name=item_id,
                                             atom=atom, shape=data.shape, filters=filters)
        data_array[:] = data
        self.table.flush()

    def get_group(self, parent, group_id):
        return parent.__getattr__(group_id)

    def get_data(self, group, item_id):
        # We're calling read, because else we get a pytables object
        if hasattr(group, item_id):
            return group.__getattr__(item_id).read()

    def remove_group(self, where, name, recursive=True):
        # Recursive remove is on by default
        self.table.remove_node(where=where, name=name, recursive=recursive)
        self.table.flush()

    def remove_row(self, table, name_id, item_id):
        """
        # Table.remove_rows(start=None, stop=None, step=None)
        # Note removing a single row can be done using the specific remove_row() method.
        This should receive the index of the row to remove
        """
        condition = "({} == '{}')".format(name_id, item_id)
        index = table.get_where_list(condition)[0]
        try:
            table.remove_rows(start=index, stop=index+1)
        except NotImplementedError:
            # If we're removing the last row, we can just delete the whole table
            self.table.remove_node(where=table, recursive=True)

        self.table.flush()

    def close_table(self):
        """
        Make sure we clean up after ourselves
        """
        self.table.close()
        #tables.file.close_open_files()


class SubjectsTable(Table):
    class Subjects(tables.IsDescription):
        subject_id = tables.StringCol(64)
        first_name = tables.StringCol(32)
        last_name = tables.StringCol(32)
        address = tables.StringCol(32)
        city = tables.StringCol(32)
        phone = tables.StringCol(32)
        email = tables.StringCol(32)
        birthday = tables.StringCol(32)
        mass = tables.FloatCol()

    def __init__(self, table):
        super(SubjectsTable, self).__init__(table=table)
        self.table_name = "subject"

        # Check if table has subjects table
        if 'subjects' not in self.table.root:
            self.subjects_table = self.table.create_table(where="/", name="subjects", description=SubjectsTable.Subjects,
                                                         title="Subjects", filters=self.filters)
        else:
            self.subjects_table = self.table.root.subjects

        self.column_names = self.subjects_table.colnames

    def create_subject(self, **kwargs):
        # I need at least a last_name, probably some other value too...
        if "first_name" not in kwargs and "last_name" not in kwargs and "birthday" not in kwargs:
            raise MissingIdentifier("I need at least a first name, last name and birthday")

        self.check_availability(self.subjects_table, "subject_id", kwargs)

        self.create_row(self.subjects_table, **kwargs)
        group = self.create_group(parent=self.table.root, item_id=kwargs["subject_id"])
        return group

    def get_new_id(self):
        subjects = self.get_subjects()
        max_id = len(subjects)
        for subject in subjects:
            subject_id = int(subject["subject_id"].split("_")[-1])
            if subject_id > max_id:
                max_id = subject_id

        max_id += 1
        return "{}_{}".format(self.table_name, max_id)

    def get_subject(self, plate="", last_name="", birthday=""):
        return self.search_table(self.subjects_table, first_name=plate,
                                 last_name=last_name, birthday=birthday)

    def get_subjects(self):
        subject_list = self.subjects_table.read()
        subjects = []
        for s in subject_list:
            subject = defaultdict()
            for key, value in zip(self.column_names, s):
                subject[key] = value
            subjects.append(subject)
        return subjects


class SessionsTable(Table):
    class Sessions(tables.IsDescription):
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        session_name = tables.StringCol(32)
        session_date = tables.StringCol(32)
        session_time = tables.StringCol(32)

    class SessionLabels(tables.IsDescription):
        session_id = tables.StringCol(64)
        session_label = tables.StringCol(64)

    def __init__(self, table, subject_id):
        super(SessionsTable, self).__init__(table=table)
        self.table_name = "session"
        self.subject_id = subject_id
        self.subject_group = self.table.root.__getattr__(self.subject_id)

        if 'sessions' not in self.subject_group:
            self.table.create_table(where=self.subject_group, name="sessions", description=SessionsTable.Sessions,
                                   title="Sessions", filters=self.filters)
        # These are separated, because I sometimes remove one without the other (for now)
        if "session_labels" not in self.subject_group:
            self.table.create_table(where=self.subject_group, name="session_labels",
                                   description=SessionsTable.SessionLabels, title="Session Labels",
                                   filters=self.filters)

        self.sessions_table = self.subject_group.sessions
        self.column_names = self.sessions_table.colnames

    def create_session(self, **kwargs):
        if "session_name" not in kwargs:
            raise MissingIdentifier("I need at least a session name")

        self.check_availability(self.sessions_table, "session_id", kwargs)

        self.create_row(self.sessions_table, **kwargs)
        group = self.create_group(parent=self.subject_group, item_id=kwargs["session_id"])
        return group

    def get_new_id(self):
        sessions = self.get_sessions()
        max_id = len(sessions)
        for session in sessions:
            session_id = int(session["session_id"].split("_")[-1])
            if session_id > max_id:
                max_id = session_id

        max_id += 1
        return "{}_{}".format(self.table_name, max_id)

    def get_session(self, session_name=""):
        return self.search_table(self.sessions_table, session_name=session_name)

    def get_sessions(self):
        session_list = self.sessions_table.read()
        sessions = []
        for s in session_list:
            session = defaultdict()
            for key, value in zip(self.column_names, s):
                session[key] = value
            sessions.append(session)
        return sessions

# TODO: See if you can reduce the precision, so we don't needlessly waste tons and tons of space
class MeasurementsTable(Table):
    class Measurements(tables.IsDescription):
        measurement_id = tables.StringCol(64)
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        plate_id = tables.StringCol(64)
        measurement_name = tables.StringCol(64)
        number_of_frames = tables.UInt32Col()
        number_of_rows = tables.UInt32Col()
        number_of_columns = tables.UInt32Col()
        frequency = tables.UInt32Col()
        orientation = tables.BoolCol()
        maximum_value = tables.FloatCol()
        date = tables.StringCol(32)
        time = tables.StringCol(32)
        processed = tables.BoolCol()

    def __init__(self, table, subject_id, session_id):
        super(MeasurementsTable, self).__init__(table=table)
        self.table_name = "measurement"
        self.subject_id = subject_id
        self.session_id = session_id

        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)

        if 'measurements' not in self.session_group:
            self.measurements_table = self.table.create_table(where=self.session_group, name="measurements",
                                                             description=MeasurementsTable.Measurements,
                                                             title="Measurements", filters=self.filters)

        if 'contacts' not in self.session_group:
            self.contacts_table = self.table.create_table(where=self.session_group, name="contacts",
                                                         description=SessionDataTable.Contacts,
                                                         title="Contacts", filters=self.filters)

        self.contacts_table = self.session_group.contacts
        self.measurements_table = self.session_group.measurements
        self.column_names = self.measurements_table.colnames

    def create_measurement(self, **kwargs):
        if "measurement_name" not in kwargs:
            raise MissingIdentifier("I need at least a measurement name")

        self.check_availability(self.measurements_table, "measurement_id", kwargs)

        self.create_row(self.measurements_table, **kwargs)
        group = self.create_group(parent=self.session_group, item_id=kwargs["measurement_id"])
        return group

    def get_new_id(self):
        measurements = self.get_measurements()
        max_id = len(measurements)
        for measurement in measurements:
            measurement_id = int(measurement["measurement_id"].split("_")[-1])
            if measurement_id > max_id:
                max_id = measurement_id

        max_id += 1
        return "{}_{}".format(self.table_name, max_id)

    def get_measurement(self, measurement_name=""):
        return self.search_table(self.measurements_table, measurement_name=measurement_name)

    def get_measurements(self):
        measurement_list = self.measurements_table.read()
        measurements = []
        for m in measurement_list:
            measurement = defaultdict()
            for column, value in zip(self.column_names, m):
                measurement[column] = value
            measurements.append(measurement)
        return measurements

    def update_measurement(self, item_id, **kwargs):
        for row in self.measurements_table:
            if row["measurement_id"] == item_id:
                for attr, value in kwargs.items():
                    row[attr] = value
                row.update()
        self.measurements_table.flush()


class ContactsTable(Table):
    class Contacts(tables.IsDescription):
        measurement_id = tables.StringCol(64)
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        contact_id = tables.StringCol(16)
        contact_label = tables.Int16Col()
        orientation = tables.BoolCol()
        min_x = tables.UInt16Col()
        max_x = tables.UInt16Col()
        min_y = tables.UInt16Col()
        max_y = tables.UInt16Col()
        min_z = tables.UInt16Col()
        max_z = tables.UInt16Col()
        width = tables.UInt16Col()
        height = tables.UInt16Col()
        length = tables.UInt16Col()
        invalid = tables.BoolCol()
        filtered = tables.BoolCol()
        unfinished_contact = tables.BoolCol()
        edge_contact = tables.BoolCol()
        incomplete_contact = tables.BoolCol()

        vertical_impulse = tables.FloatCol()
        time_of_peak_force = tables.FloatCol()
        peak_force = tables.FloatCol()
        peak_pressure = tables.FloatCol()
        peak_surface = tables.FloatCol()

        # Spatiotemporal results
        gait_pattern = tables.StringCol(16)
        gait_velocity = tables.FloatCol()
        stance_duration = tables.FloatCol()
        swing_duration = tables.FloatCol()
        stance_percentage = tables.FloatCol()

        stride_duration = tables.FloatCol()
        stride_length = tables.FloatCol()
        stride_width = tables.FloatCol()

        step_duration = tables.FloatCol()
        step_length = tables.FloatCol()
        step_width = tables.FloatCol()

        ipsi_duration = tables.FloatCol()
        ipsi_length = tables.FloatCol()
        ipsi_width = tables.FloatCol()

        diag_duration = tables.FloatCol()
        diag_length = tables.FloatCol()
        diag_width = tables.FloatCol()

    def __init__(self, table, subject_id, session_id, measurement_id):
        super(ContactsTable, self).__init__(table=table)
        self.table_name = "contact"
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.measurement_group = self.session_group.__getattr__(measurement_id)

        if 'contacts' not in self.measurement_group:
            self.contacts_table = self.table.create_table(where=self.measurement_group, name="contacts",
                                                         description=ContactsTable.Contacts,
                                                         title="Contacts", filters=self.filters)

        self.contacts_table = self.measurement_group.contacts
        self.column_names = self.contacts_table.colnames

    def create_contact(self, **kwargs):
        if "contact_id" not in kwargs:
            raise MissingIdentifier("I need at least a contact id")

        self.check_availability(self.contacts_table, "contact_id", kwargs)

        self.create_row(self.contacts_table, **kwargs)
        group = self.create_group(parent=self.measurement_group, item_id=kwargs["contact_id"])
        return group

    def get_new_id(self):
        contacts = self.get_contacts()
        max_id = len(contacts)
        for contact in contacts:
            contact_id = int(contact["contact_id"].split("_")[-1])
            if contact_id > max_id:
                max_id = contact_id

        max_id += 1
        return "{}_{}".format(self.table_name, max_id)

    def update_contact(self, **kwargs):
        found = False
        for row in self.contacts_table:
            if row["contact_id"] == kwargs["contact_id"]:
                found = True
                # Update any fields that have changed
                for key, value in kwargs.items():
                    row[key] = value
                    row.update()
        if found:
            self.contacts_table.flush()
            return True
        return False

    def get_contact(self, contact_id=""):
        return self.search_table(self.contacts_table, contact_id=contact_id)

    def get_contacts(self):
        contact_list = self.contacts_table.read()
        contacts = []
        for c in contact_list:
            contact = defaultdict()
            for column, value in zip(self.column_names, c):
                contact[column] = value
            contacts.append(contact)
        return contacts


class ContactDataTable(Table):
    def __init__(self, table, subject_id, session_id, measurement_id):
        super(ContactDataTable, self).__init__(table=table)
        self.table_name = "contact_data"
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.measurement_group = self.session_group.__getattr__(measurement_id)
        self.item_ids = ["data", "max_of_max", "pressure_over_time", "force_over_time", "surface_over_time",
                         "pixel_count_over_time", "cop_x", "cop_y", "vcop_xy", "vcop_x", "vcop_y",]

    def get_contact_data(self):
        contacts = []
        for contact in self.measurement_group.contacts:
            contact_id = contact["contact_id"]
            group = self.measurement_group.__getattr__(contact_id)
            contact_data = defaultdict()
            for item_id in self.item_ids:
                # We try to retrieve what's available, if its not available, it should be computed later on
                try:
                    contact_data[item_id] = group.__getattr__(item_id).read()
                except NoSuchNodeError:
                    contact_data[item_id] = None
            contacts.append(contact_data)
        return contacts

class SessionDataTable(Table):
    class Contacts(tables.IsDescription):
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        contact_label = tables.Int16Col()
        orientation = tables.BoolCol()
        min_x = tables.UInt16Col()
        max_x = tables.UInt16Col()
        min_y = tables.UInt16Col()
        max_y = tables.UInt16Col()
        min_z = tables.UInt16Col()
        max_z = tables.UInt16Col()
        width = tables.UInt16Col()
        height = tables.UInt16Col()
        length = tables.UInt16Col()

    def __init__(self, table, subject_id, session_id):
        super(SessionDataTable, self).__init__(table=table)
        self.table_name = "session_data"
        self.subject_id = subject_id
        self.session_id = session_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.item_ids = ["data", "max_of_max", "pressure_over_time", "force_over_time", "surface_over_time",
                         "cop_x", "cop_y"]

    def get_contact_data(self):
        contacts = []
        for contact in self.session_group.contacts:
            contact_label = contact["contact_label"]
            group = self.session_group.__getattr__(contact_label)
            contact_data = defaultdict()
            for item_id in self.item_ids:
                contact_data[item_id] = group.__getattr__(item_id).read()
            contacts.append(contact_data)
        return contacts

class PlatesTable(Table):
    class Plates(tables.IsDescription):
        plate_id = tables.StringCol(64)
        brand = tables.StringCol(32)
        model = tables.StringCol(32)
        number_of_rows = tables.Int16Col()
        number_of_columns = tables.Int16Col()
        sensor_width = tables.FloatCol()
        sensor_height = tables.FloatCol()
        sensor_surface = tables.FloatCol()

    def __init__(self, table):
        super(PlatesTable, self).__init__(table=table)
        self.table_name = "plate"

        if 'plates' not in self.table.root:
            self.plates_table = self.table.create_table(where="/", name="plates", description=PlatesTable.Plates,
                                                       title="Plates", filters=self.filters)
        else:
            self.plates_table = self.table.root.plates

        self.column_names = self.plates_table.colnames

    def create_plate(self, **kwargs):
        # I need at least a plate and model
        if "brand" not in kwargs and "model" not in kwargs:
            raise MissingIdentifier("I need at least a brand and a model")

        self.create_row(self.plates_table, **kwargs)

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.plates_table))

    def get_plate(self, brand="", model=""):
        return self.search_table(self.plates_table, brand=brand, model=model)

    def get_plates(self):
        plates_list = self.plates_table.read()
        plates = []
        for s in plates_list:
            plate = defaultdict()
            for key, value in zip(self.column_names, s):
                plate[key] = value
            plates.append(plate)
        return plates


def verify_tables(table):
    # If there isn't even a subjects table, no need to do anything
    if not hasattr(table.root,  "subjects"):
        return

    # Check SubjectsTable
    subjects_description = table.root.subjects.description._v_dtypes
    subject_difference = False
    for key, value in SubjectsTable.Subjects.columns.items():
        if value.dtype != subjects_description.get(key):
            subject_difference = True

    # If there are any differences, copy over the content to a new table and then replace the old table with the new one
    if subject_difference:
        root_group = table.root
        new_subjects_table = table.createTable(where="/", name="subjects2",
                                               description=SubjectsTable.Subjects,
                                               title="Subjects", filters=table.filters)
        subjects_table = table.root.subjects
        subjects_table.attrs._f_copy(new_subjects_table)
        for i in xrange(subjects_table.nrows):
            new_subjects_table.row.append()
        new_subjects_table.flush()

        description = table.description._v_colObjects
        for col in description:
            getattr(new_subjects_table.cols, col)[:] = getattr(subjects_table.cols, col)[:]

        subjects_table.remove()
        new_subjects_table.move(root_group, "subjects")

    # Check SessionsTable
    for subject in table.root.subjects:
        session_difference = False
        subject_id = subject["subject_id"]
        subject_group = table.root.__getattr__(subject_id)
        sessions_description = subject_group.sessions.description._v_dtypes
        for key, value in SessionsTable.Sessions.columns.items():
            if value.dtype != sessions_description.get(key):
                session_difference = True

        if session_difference:
            new_sessions_table = table.createTable(where="/", name="sessions2",
                                                   description=SessionsTable.Sessions,
                                                   title="Sessions", filters=table.filters)
            sessions_table = subject_group.sessions
            sessions_table.attrs._f_copy(new_sessions_table)
            for i in xrange(sessions_table.nrows):
                new_sessions_table.row.append()
            new_sessions_table.flush()

            description = sessions_table.description._v_colObjects
            for col in description:
                getattr(new_sessions_table.cols, col)[:] = getattr(sessions_table.cols, col)[:]

            sessions_table.remove()
            new_sessions_table.move(subject_group, "sessions")

        # Check the MeasurementsTable
        for session in table.root.__getattr__(subject_id).sessions:
            measurement_difference = False
            session_id = session["session_id"]
            session_group = table.root.__getattr__(subject_id).__getattr__(session_id)
            measurements_description = session_group.measurements.description._v_dtypes
            for key, value in MeasurementsTable.Measurements.columns.items():
                if value.dtype != measurements_description.get(key):
                    measurement_difference = True

            if measurement_difference:
                new_measurements_table = table.createTable(where="/", name="measurements2",
                                                           description=MeasurementsTable.Measurements,
                                                           title="Measurements", filters=table.filters)
                measurements_table = session_group.measurements
                measurements_table.attrs._f_copy(new_measurements_table)
                for i in xrange(measurements_table.nrows):
                    new_measurements_table.row.append()
                new_measurements_table.flush()

                description = measurements_table.description._v_colObjects
                for col in description:
                    getattr(new_measurements_table.cols, col)[:] = getattr(measurements_table.cols, col)[:]

                measurements_table.remove()
                new_measurements_table.move(session_group, "measurements")

            for measurement in table.root.__getattr__(subject_id).__getattr__(session_id).measurements:
                contact_difference = False
                measurement_id = measurement["measurement_id"]
                measurement_group = table.root.__getattr__(subject_id).__getattr__(session_id).__getattr__(measurement_id)
                contacts_description = measurement_group.contacts.description._v_dtypes
                for key, value in ContactsTable.Contacts.columns.items():
                    if value.dtype != contacts_description.get(key):
                        contact_difference = True

                if contact_difference:
                    new_contacts_table = table.createTable(where="/", name="contacts2",
                                                               description=ContactsTable.Contacts,
                                                               title="Contacts", filters=table.filters)
                    contacts_table = measurement_group.contacts
                    contacts_table.attrs._f_copy(new_contacts_table)
                    for i in xrange(contacts_table.nrows):
                        new_contacts_table.row.append()
                    new_contacts_table.flush()

                    description = contacts_table.description._v_colObjects
                    for col in description:
                        getattr(new_contacts_table.cols, col)[:] = getattr(contacts_table.cols, col)[:]

                    contacts_table.remove()
                    new_contacts_table.move(measurement_group, "contacts")

    return True

def load_table(database_file):
    return tables.open_file(database_file, mode="a", title="Data")