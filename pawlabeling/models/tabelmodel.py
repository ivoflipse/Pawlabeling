import tables


class MissingIdentifier(Exception):
    pass

# I should add some helper function to check if something can be found, if not raise an exception or log something
class Table(object):
    def __init__(self):
        # Make this configurable
        self.table = tables.openFile("data.h5", mode="a", title="Data")
        self.table_name = "table"

    def create_row(self, table, **kwargs):
        row = table.row

        for attr, value in kwargs.iteritems():
            row[attr] = value

        # Append the row to the table
        row.append()
        # Flush the changes
        table.flush()

    def get_new_id(self, table):
        return "{}_{}".format(self.table_name, len(table))

    def create_group(self, parent, item_id):
        group = self.table.createGroup(where=parent, name=item_id)
        self.table.flush()
        return group

    # TODO I removed the assertion to check whether we have multiple hits
    # Though in practice this should NOT be possible
    def search_table(self, table, **kwargs):
        # Create a query out of the kwargs
        query = " & ".join(
            ["({} == '{}')".format(key, value) for key, value in kwargs.items() if value != ""])
        rows = table.readWhere(query)
        return rows

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

    def __init__(self):
        super(SubjectsTable, self).__init__()
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

        # TODO Add some other validation to see if the input values are correct

        # Check if the subject is already in the table
        if self.get_subject(first_name=kwargs["first_name"],
                            last_name=kwargs["last_name"], birthday=kwargs["birthday"]):
            print "Subject already exists"
            return -1

        subject_id = self.get_new_id(self.subjects_table)
        kwargs["subject_id"] = subject_id

        self.create_row(self.subjects_table, **kwargs)
        group = self.create_group(parent=self.table.root, item_id=subject_id)
        print "Subject created"
        return group

    def get_subject(self, first_name="", last_name="", birthday=""):
        return self.search_table(self.subjects_table, first_name=first_name,
                                 last_name=last_name, birthday=birthday)

    def get_subjects(self, **kwargs):
        if kwargs["first_name"] or kwargs["last_name"]:
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

    def __init__(self, subject_id):
        super(SessionsTable, self).__init__()
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

        # Check if the session isn't already in the table
        if self.get_session_row(self.sessions_table, session_name=kwargs["session_name"]):
            print "Session already exists"
            return -1

        # How many sessions do we already have?
        session_id = self.get_new_id(self.sessions_table)
        kwargs["session_id"] = session_id

        self.create_row(self.sessions_table, **kwargs)
        group = self.create_group(parent=self.subject_group, item_id=session_id)
        print "Session created"
        return group

    def get_session_row(self, table, session_name=""):
        return self.search_table(table, session_name=session_name)

    def get_sessions(self, **kwargs):
        if kwargs["session_name"]:
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


class MeasurementsTable(Table):
    class Measurements(tables.IsDescription):
        measurement_id = tables.StringCol(64)
        session_id = tables.StringCol(64)
        subject_id = tables.StringCol(64)
        measurement_name = tables.StringCol(64)
        number_of_frames = tables.UInt32Col()
        number_of_rows = tables.UInt32Col()
        number_of_cols = tables.UInt32Col()
        measurement_frequency = tables.UInt32Col()
        brand = tables.StringCol(32)
        model = tables.StringCol(32)
        date = tables.StringCol(32)
        time = tables.StringCol(32)

    def __init__(self, subject_id, session_id):
        super(MeasurementsTable, self).__init__()
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

        if self.get_measurement_row(self.measurements_table, measurement_name=kwargs["measurement_name"]):
            print "Measurement already exists"
            return -1

        measurement_id = self.get_new_id(self.measurements_table)
        kwargs["measurement_id"] = measurement_id

        self.create_row(self.measurements_table, **kwargs)
        group = self.create_group(parent=self.session_group, item_id=measurement_id)
        print "Measurement created"
        return group

    def get_measurement_row(self, table, measurement_name=""):
        return self.search_table(table, measurement_name=measurement_name)

    def get_measurements(self, **kwargs):
        if kwargs["measurement_name"]:
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
        contact_id = tables.UInt16Col()
        label = tables.UInt16Col()
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

    def __init__(self, subject_id, session_id, measurement_id):
        super(ContactsTable, self).__init__()
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

        if self.get_contact_row(self.contacts_table, contact_id=kwargs["contact_id"]):
            print "Contact already exists"
            return -1

        self.create_row(self.contacts_table, **kwargs)
        group = self.create_group(parent=self.measurement_group, item_id=kwargs["contact_id"])
        print "Contact created"
        return group

    def get_contact_row(self, table, contact_id=""):
        return self.search_table(table, contact_id=contact_id)

    def get_contacts(self, **kwargs):
        contact_list = self.contacts_table.read()
        contacts = []
        for c in contact_list:
            contact = {}
            for column, value in zip(self.column_names, c):
                contact[column] = value
            contacts.append(contact)
        return contacts


# This function can be used for data, contact_data and normalized_contact_data
# Actually also for all the different results (at least the time series)
# TODO: check if I'm not creating duplicate data, so check if the item_id already exists in the group
def store_data(table, group, item_id, data):
    atom = tables.Atom.from_dtype(data.dtype)
    filters = tables.Filters(complib="blosc", complevel=9)
    data_array = table.createCArray(where=group, name=item_id,
                                    atom=atom, shape=data.shape, filters=filters)
    data_array[:] = data
    table.flush()
