import numpy as np
import tables
import datetime
import uuid
import os
from pawlabeling.functions import io

DATADIR = "C:\Exports2"


def actual_kwargs():
    """
    Decorator that provides the wrapped function with an attribute 'actual_kwargs'
    containing just those keyword arguments actually passed in to the function.
    Source Stack Overflow:
    http://stackoverflow.com/questions/1408818/getting-the-the-keyword-arguments-actually-passed-to-a-python-method
    """

    def decorator(function):
        def inner(*args, **kwargs):
            inner.actual_kwargs = kwargs
            return function(*args, **kwargs)

        return inner

    return decorator


class Subjects(tables.IsDescription):
    subject_id = tables.StringCol(64)
    first_name = tables.StringCol(32)
    last_name = tables.StringCol(32)
    address = tables.StringCol(32)
    city = tables.StringCol(32)
    postal_code = tables.StringCol(32)
    phone = tables.StringCol(32)
    email = tables.StringCol(32)
    birthday = tables.StringCol(32)
    mass = tables.Float32Col()


class Sessions(tables.IsDescription):
    session_id = tables.StringCol(64)
    subject_id = tables.StringCol(64)
    session_name = tables.StringCol(32)
    date = tables.StringCol(32)
    time = tables.StringCol(32)

# Store session labels as a key/value store
# You can have multiple labels per session this way
class SessionLabels(tables.IsDescription):
    session_id = tables.StringCol(64)
    session_label = tables.StringCol(64)


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


def main():
    # Open in append mode
    with tables.openFile("data.h5", mode="a", title="Data") as h5file:
        for directory_name in os.listdir(DATADIR)[:3]:
            file_path = os.path.join(DATADIR, directory_name)
            if os.path.isdir(file_path):
                subject_name = directory_name
                print subject_name

                # Using the subject name is a REALLY bad idea, chances of dupes is too high
                subject_group = h5file.createGroup(where="/", name=subject_name)

                # Here we need to squeeze in a session
                walking_group = h5file.createGroup(where=subject_group, name="walk")
                running_group = h5file.createGroup(where=subject_group, name="run")

                for file_name in os.listdir(file_path):
                    # I don't always know if the file will have a date string...
                    #measurement_name, date_string, _ = filename.split(' - ')
                    measurement_name = file_name

                    print file_name

                    with open(os.path.join(file_path, file_name), "r") as infile:
                        datafile = io.load(infile.read())

                    atom = tables.Atom.from_dtype(datafile.dtype)
                    filters = tables.Filters(complib="blosc", complevel=9)

                    # Have some default setting to fall back on if none is supplied
                    location = walking_group
                    if file_name[0] == 'd':
                        location = running_group
                    elif file_name[0] == "s":
                        location = walking_group

                    measurement_array = h5file.createCArray(where=location, name=measurement_name,
                                                            atom=atom, shape=datafile.shape, filters=filters)
                    measurement_array[:] = datafile
                    measurement_array.attrs['name'] = measurement_name
                    #measurement_array.attrs['date'] = date_string
                    #measurement_group.create_dataset('pressure', data=data, compression='gzip')

        h5file.close()

# I should add some helper function to check if something can be found, if not raise an exception or log something
class Table(object):
    def __init__(self):
        # Make this configurable
        self.table = tables.openFile("data.h5", mode="a", title="Data")

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
        return group

    def get_group(self, parent, item_id):
        group = parent.__getattr__(item_id)
        return group

    def close_table(self):
        """
        Make sure we clean up after ourselves
        """
        self.table.close()
        #tables.file.close_open_files()


class SubjectsTable(Table):
    """
        The Subjects Table consist out of:
            subject_id = tables.StringCol(64)
            first_name = tables.StringCol(32)
            last_name = tables.StringCol(32)
            address = tables.StringCol(32)
            city = tables.StringCol(32)
            postal_code = tables.StringCol(32)
            phone = tables.StringCol(32)
            email = tables.StringCol(32)
            birthday = tables.StringCol(32)
            mass = tables.Float32Col()
    """

    def __init__(self):
        super(SubjectsTable, self).__init__()
        # Check if table has subjects table
        if 'subjects' not in self.table.root:
            self.subjects_table = self.table.createTable(where="/", name="subjects", description=Subjects,
                                                         title="Subjects")

    def create_subject(self, **kwargs):
        # I need at least a last_name, probably some other value too...
        if "last_name" not in kwargs:
            print "I need at least a last_name to function"

        # Add some other validation to see if the input values are correct

        # Get the subject table
        self.subjects_table = self.table.root.subjects
        # How many subjects do we already have?
        subject_count = len(self.subjects_table)
        subject_id = "subject_" + str(subject_count)
        # Add the subject_id to the key word arguments
        kwargs["subject_id"] = subject_id
        self.create_row(self.subjects_table, **kwargs)
        self.create_group(parent=self.table.root, item_id=subject_id)


class SessionsTable(Table):
    """
        The Sessions Table consist out of:
            session_id = tables.StringCol(64)
            subject_id = tables.StringCol(64)
            session_name = tables.StringCol(32)
            date = tables.StringCol(32)
            time = tables.StringCol(32)
        For each session_id a new group is created
    """

    def __init__(self, subject_id):
        super(SessionsTable, self).__init__()
        self.subject_id = subject_id
        self.subject_group = self.table.root.__getattr__(self.subject_id)

        if 'sessions' not in self.subject_group:
            self.table.createTable(where=self.subject_group, name="sessions", description=Sessions, title="Sessions")
            self.table.createTable(where=self.subject_group, name="session_labels", description=Sessions,
                                   title="Session Labels")

    def create_session(self, **kwargs):
        if "session_name" not in kwargs:
            print "I need at least a session name"

        # Get the sessions table
        self.sessions_table = self.subject_group.__getattr__("sessions")
        # How many sessions do we already have?
        session_count = len(self.sessions_table)
        session_id = "session_" + str(session_count)
        kwargs["session_id"] = session_id
        self.create_row(self.sessions_table, **kwargs)
        self.create_group(parent=self.subject_group, item_id=session_id)


class MeasurementsTable(Table):
    """
        Description of the measurements table:
            measurement_id = tables.StringCol(64)
            session_id = tables.StringCol(64)
            subject_id = tables.StringCol(64)
            measurement_name = tables.StringCol(64)
            data_id = tables.StringCol(64)
            number_of_frames = tables.UInt32Col()
            number_of_rows = tables.UInt32Col()
            number_of_cols = tables.UInt32Col()
            measurement_frequency = tables.UInt32Col()
            brand = tables.StringCol(32)
            model = tables.StringCol(32)
            date = tables.StringCol(32)
            time = tables.StringCol(32)
        The actual data is stored in the MeasurementsGroup under the data_id
    """

    def __init__(self, subject_id, session_id):
        super(MeasurementsTable, self).__init__()
        self.subject_id = subject_id
        self.session_id = session_id

        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)

        if 'measurements' not in self.session_group:
            self.measurements_table = self.table.createTable(where=self.session_group, name="measurements",
                                                             description=Measurements,
                                                             title="Measurements")

    def create_measurement(self, **kwargs):
        if "measurement_name" not in kwargs:
            print "I need at least a measurement name"
        self.measurements_table = self.session_group.measurements

        measurement_count = len(self.measurements_table)
        measurement_id = "measurement_" + str(measurement_count)
        kwargs["measurement_id"] = measurement_id

        self.create_row(self.measurements_table, **kwargs)
        self.create_group(parent=self.session_group, item_id=measurement_id)


class DataTable(Table):
    def __init__(self, subject_id, session_id):
        super(DataTable, self).__init__()
        self.subject_id = subject_id
        self.session_id = session_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)

    def create_data(self, measurement_id, data):
        measurement_group = self.session_group.__getattr__(measurement_id)
        atom = tables.Atom.from_dtype(data.dtype)
        filters = tables.Filters(complib="blosc", complevel=9)
        data_array = self.table.createCArray(where=measurement_group, name=measurement_id,
                                             atom=atom, shape=data.shape, filters=filters)
        data_array[:] = data


class ContactsTable(Table):
    """
        Description of the contacts table:
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
    """

    def __init__(self, subject_id, session_id, measurement_id):
        super(ContactsTable, self).__init__()
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.measurement_group = self.session_group.__getattr__(measurement_id)

        if 'contacts' not in self.measurement_group:
            self.contacts_table = self.table.createTable(where=self.measurement_group, name="contacts",
                                                         description=Contacts,
                                                         title="Contacts")

    def create_contact(self, **kwargs):
        self.contacts_table = self.measurement_group.contacts

        # I would actually want to use the
        contact_count = len(self.contacts_table)
        contact_id = "contact_" + str(contact_count)

        kwargs["contact_id"] = contact_id

        self.create_row(self.contacts_table, **kwargs)
        self.create_group(parent=self.measurement_group, item_id=contact_id)

def store_contact_data(table, contact_group, contact_id, data):
    atom = tables.Atom.from_dtype(data.dtype)
    filters = tables.Filters(complib="blosc", complevel=9)
    data_array = table.createCArray(where=contact_group, name=contact_id,
                                         atom=atom, shape=data.shape, filters=filters)
    data_array[:] = data

class ContactDataTable(Table):
    def __init__(self, subject_id, session_id, measurement_id, contact_id):
        super(ContactDataTable, self).__init__()
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.contact_id = contact_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.contact_group = self.session_group.__getattr__(self.measurement_id).__getattr__(self.contact_id)

    def create_data(self, data):
        atom = tables.Atom.from_dtype(data.dtype)
        filters = tables.Filters(complib="blosc", complevel=9)
        data_array = self.table.createCArray(where=self.contact_group, name=self.contact_id,
                                             atom=atom, shape=data.shape, filters=filters)
        data_array[:] = data

class NormalizedContactDataTable(Table):
    def __init__(self, subject_id, session_id, measurement_id, contact_id):
        super(NormalizedContactDataTable, self).__init__()
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.contact_id = contact_id
        self.session_group = self.table.root.__getattr__(self.subject_id).__getattr__(self.session_id)
        self.contact_group = self.session_group.__getattr__(self.measurement_id).__getattr__(self.contact_id)

    def create_data(self, data):
        atom = tables.Atom.from_dtype(data.dtype)
        filters = tables.Filters(complib="blosc", complevel=9)
        data_array = self.table.createCArray(where=self.contact_group, name=self.contact_id,
                                             atom=atom, shape=data.shape, filters=filters)
        data_array[:] = data