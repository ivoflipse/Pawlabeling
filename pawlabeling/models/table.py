import tables

class MissingIdentifier(Exception):
    pass

# I should add some helper function to check if something can be found, if not raise an exception or log something
class Table(object):
    def __init__(self, database_file):
        # Make this configurable
        self.table = tables.openFile(database_file, mode="a", title="Data")
        self.table_name = "table"

    def create_row(self, table, **kwargs):
        row = table.row

        for attr, value in kwargs.iteritems():
            row[attr] = value

        # Append the row to the table
        row.append()
        # Flush the changes
        table.flush()

    def create_group(self, parent, item_id):
        group = self.table.createGroup(where=parent, name=item_id)
        self.table.flush()
        return group

    # Though in practice this should NOT be possible
    def search_table(self, table, **kwargs):
        # Create a query out of the kwargs
        query = " & ".join(
            ["({} == '{}')".format(key, value) for key, value in kwargs.items() if value != ""])
        print query
        rows = table.readWhere(query)
        return rows

    # This function can be used for measurement_data, contact_data and normalized_contact_data
    # Actually also for all the different results (at least the time series)
    # TODO: check if I'm not creating duplicate measurement_data, so check if the item_id already exists in the group
    def store_data(self, group, item_id, data):
        atom = tables.Atom.from_dtype(data.dtype)
        filters = tables.Filters(complib="blosc", complevel=9)
        data_array = self.table.createCArray(where=group, name=item_id,
                                        atom=atom, shape=data.shape, filters=filters)
        data_array[:] = data
        self.table.flush()

    def get_group(self, parent, group_id):
        return parent.__getattr__(group_id)

    def get_data(self, group, item_id):
        # We're calling read, because else we get a pytables object
        if hasattr(group, item_id):
            return group.__getattr__(item_id).read()

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
        mass = tables.Float32Col()

    def __init__(self, database_file):
        super(SubjectsTable, self).__init__(database_file=database_file)
        self.table_name = "subject"

        # Check if table has subjects table
        if 'subjects' not in self.table.root:
            self.subjects_table = self.table.createTable(where="/", name="subjects", description=SubjectsTable.Subjects,
                                                         title="Subjects")
        else:
            self.subjects_table = self.table.root.subjects

        self.column_names = self.subjects_table.colnames

    def create_subject(self, **kwargs):
        # I need at least a last_name, probably some other value too...
        if "first_name" not in kwargs and "last_name" not in kwargs and "birthday" not in kwargs:
            raise MissingIdentifier("I need at least a first name, last name and birthday")

        self.create_row(self.subjects_table, **kwargs)
        group = self.create_group(parent=self.table.root, item_id=kwargs["subject_id"])
        return group

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.subjects_table))

    def get_subject(self, plate="", last_name="", birthday=""):
        return self.search_table(self.subjects_table, first_name=plate,
                                 last_name=last_name, birthday=birthday)

    def get_subjects(self, **kwargs):
        if kwargs.get("first_name", None) or kwargs.get("last_name", None):
            subject_list = self.search_table(self.subjects_table, **kwargs)
        else:
            subject_list = self.subjects_table.read()

        subjects = []
        for s in subject_list:
            subject = {}
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

    def __init__(self, database_file, subject_id):
        super(SessionsTable, self).__init__(database_file=database_file)
        self.table_name = "session"
        self.subject_id = subject_id
        self.subject_group = self.table.root.__getattr__(self.subject_id)

        if 'sessions' not in self.subject_group:
            self.table.createTable(where=self.subject_group, name="sessions", description=SessionsTable.Sessions,
                                   title="Sessions")
            self.table.createTable(where=self.subject_group, name="session_labels",
                                   description=SessionsTable.SessionLabels, title="Session Labels")

        self.sessions_table = self.subject_group.sessions
        self.column_names = self.sessions_table.colnames

    def create_session(self, **kwargs):
        if "session_name" not in kwargs:
            raise MissingIdentifier("I need at least a session name")

        self.create_row(self.sessions_table, **kwargs)
        group = self.create_group(parent=self.subject_group, item_id=kwargs["session_id"])
        return group

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.sessions_table))

    def get_session_row(self, session_name=""):
        return self.search_table(self.sessions_table, session_name=session_name)

    def get_sessions(self, **kwargs):
        if kwargs.get("session_name", None):
            session_list = self.search_table(self.sessions_table, **kwargs)
        else:
            session_list = self.sessions_table.read()

        sessions = []
        for s in session_list:
            session = {}
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
        maximum_value = tables.Float32Col()
        date = tables.StringCol(32)
        time = tables.StringCol(32)

    def __init__(self, database_file, subject_id, session_id):
        super(MeasurementsTable, self).__init__(database_file=database_file)
        self.table_name = "measurement"
        self.subject_id = subject_id
        self.session_id = session_id

        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)

        if 'measurements' not in self.session_group:
            self.measurements_table = self.table.createTable(where=self.session_group, name="measurements",
                                                             description=MeasurementsTable.Measurements,
                                                             title="Measurements")

        self.measurements_table = self.session_group.measurements
        self.column_names = self.measurements_table.colnames

    def create_measurement(self, **kwargs):
        if "measurement_name" not in kwargs:
            raise MissingIdentifier("I need at least a measurement name")

        self.create_row(self.measurements_table, **kwargs)
        group = self.create_group(parent=self.session_group, item_id=kwargs["measurement_id"])
        return group

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.measurements_table))

    def get_measurement_row(self, measurement_name=""):
        return self.search_table(self.measurements_table, measurement_name=measurement_name)

    def get_measurements(self, **kwargs):
        if kwargs.get("measurement_name", None):
            measurement_list = self.search_table(self.measurements_table, **kwargs)
        else:
            measurement_list = self.measurements_table.read()

        measurements = []
        for m in measurement_list:
            measurement = {}
            for column, value in zip(self.column_names, m):
                measurement[column] = value
            measurements.append(measurement)
        return measurements


class ContactsTable(Table):
    class Contacts(tables.IsDescription):
        measurement_id = tables.StringCol(64)
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        contact_id = tables.StringCol(16)
        contact_label = tables.Int16Col()  # These might also be negative...
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

    def __init__(self, database_file, subject_id, session_id, measurement_id):
        super(ContactsTable, self).__init__(database_file=database_file)
        self.table_name = "contact"
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.measurement_group = self.session_group.__getattr__(measurement_id)

        if 'contacts' not in self.measurement_group:
            self.contacts_table = self.table.createTable(where=self.measurement_group, name="contacts",
                                                         description=ContactsTable.Contacts,
                                                         title="Contacts")

        self.contacts_table = self.measurement_group.contacts
        self.column_names = self.contacts_table.colnames

    def create_contact(self, **kwargs):
        if "contact_id" not in kwargs:
            raise MissingIdentifier("I need at least a contact id")

        self.create_row(self.contacts_table, **kwargs)
        group = self.create_group(parent=self.measurement_group, item_id=kwargs["contact_id"])
        return group

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.contacts_table))

    def update_contact(self, **kwargs):
        for row in self.contacts_table:
            if row["contact_id"] == kwargs["contact_id"]:
                # Update any fields that have changed
                for key, value in kwargs.items():
                    if row[key] != value:
                        row[key] = value
                        row.update()
        self.table.flush()

    def get_contact_row(self, contact_id=""):
        return self.search_table(self.contacts_table, contact_id=contact_id)

    def get_contacts(self, **kwargs):
        contact_list = self.contacts_table.read()
        contacts = []
        for c in contact_list:
            contact = {}
            for column, value in zip(self.column_names, c):
                contact[column] = value
            contacts.append(contact)
        return contacts

class ContactDataTable(Table):
    def __init__(self, database_file, subject_id, session_id, measurement_id):
        super(ContactDataTable, self).__init__(database_file=database_file)
        self.table_name = "contact_data"
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.measurement_group = self.session_group.__getattr__(measurement_id)
        self.item_ids = ["data", "max_of_max", "pressure_over_time", "force_over_time", "surface_over_time",
                         "cop_x","cop_y"]

    def get_contact_data(self):
        contacts = []
        for contact in self.measurement_group.contacts:
            contact_id = contact["contact_id"]
            group = self.measurement_group.__getattr__(contact_id)
            contact_data = {}
            for item_id in self.item_ids:
                contact_data[item_id] = group.__getattr__(item_id).read()
            contacts.append(contact_data)
        return contacts

class PlatesTable(Table):
    """
    "plate": "rsscan",
     "model": "2m 2nd gen",
     "sensor_width": 0.508,
     "sensor_height": 0.762,
     "sensor_surface": 0.387096
    """
    class Plates(tables.IsDescription):
        plate_id = tables.StringCol(64)
        brand = tables.StringCol(32)
        model = tables.StringCol(32)
        number_of_rows = tables.Int16Col()
        number_of_columns = tables.Int16Col()
        sensor_width = tables.Float16Col()
        sensor_height = tables.Float16Col()
        sensor_surface = tables.Float16Col()

    def __init__(self, database_file):
        super(PlatesTable, self).__init__(database_file=database_file)
        self.table_name = "plate"

        if 'plates' not in self.table.root:
            self.plates_table = self.table.createTable(where="/", name="plates", description=PlatesTable.Plates,
                                                         title="Plates")
        else:
            self.plates_table = self.table.root.plates

        self.column_names = self.plates_table.colnames

    def create_plate(self, **kwargs):
        # I need at least a plate, model and frequency
        if "plate" not in kwargs and "model" not in kwargs and "frequency" not in kwargs:
            raise MissingIdentifier("I need at least a first name, last name and birthday")

        self.create_row(self.plates_table, **kwargs)
        print "Created plate", kwargs

    def get_new_id(self):
        return "{}_{}".format(self.table_name, len(self.plates_table))

    def get_plate(self, brand="", model="", frequency=""):
        return self.search_table(self.plates_table, brand=brand, model=model, frequency=frequency)

    def get_plates(self, **kwargs):
        if kwargs.get("plate", None) or kwargs.get("model", None) or kwargs.get("frequency", None):
            plates_list = self.search_table(self.plates_table, **kwargs)
        else:
            plates_list = self.plates_table.read()

        plates = []
        for s in plates_list:
            plate = {}
            for key, value in zip(self.column_names, s):
                plate[key] = value
            plates.append(plate)
        return plates