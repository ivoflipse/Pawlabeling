from collections import defaultdict
import cv2
from itertools import izip

import numpy as np
from pubsub import pub

from ..functions import utility, calculations, tracking
from ..settings import settings
from ..models import table

# from memory_profiler import profile

class Contacts(object):
    def __init__(self, subject_id, session_id, measurement_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.table = settings.settings.table
        self.contacts_table = table.ContactsTable(table=self.table,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)

    def create_contacts(self, contacts):
        """
        """
        self.delete_contacts()

        # Make sure all the results are up to date
        for contact in contacts:
            self.create_contact(contact)

        return contacts

    def create_contact(self, contact):
        # Convert the contact to a dict, like the table expects
        contact_dict = contact.to_dict()
        # This doesn't seem to have an effect, because we just deleted everything (which is stupid)
        updated = self.contacts_table.update_contact(**contact_dict)
        if not updated:
            self.contact_group = self.contacts_table.create_contact(**contact_dict)

        # We store the results separately
        array_results = {
            "data": contact.data,
            "max_of_max": contact.max_of_max,
            "force_over_time": contact.force_over_time,
            "pixel_count_over_time": contact.pixel_count_over_time,
            "pressure_over_time": contact.pressure_over_time,
            "surface_over_time": contact.surface_over_time,
            "cop_x": contact.cop_x,
            "cop_y": contact.cop_y,
            "vcop_xy": contact.vcop_xy,
            "vcop_x": contact.vcop_x,
            "vcop_y": contact.vcop_y,
        }

        for item_id, data in array_results.iteritems():
            result = self.contacts_table.get_data(group=self.contact_group, item_id=item_id)
            if not result: #result is None:
                self.contacts_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)
                # If the arrays are not equal, drop the old one and write the new data
            elif not np.array_equal(result, data):
                #print "Item: {} is not equal to the stored version".format(item_id)
                # Let's hope this will simply replace the old values
                # http://hdf-forum.184993.n3.nabble.com/hdf-forum-Reset-data-in-pytables-array-td193311.html
                # Supposedly I should use arr.__set__item(key, value)
                # But I reckon that assumes the shapes stay the same
                # Delete the old one
                self.contacts_table.remove_group(
                    where="/{}/{}/{}/{}".format(self.subject_id, self.session_id,
                                                self.measurement_id, contact.contact_id),
                    name=item_id)
                # And store the new one
                self.contacts_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)


    def delete_contacts(self):
        # Drop any existing contacts before creating new ones
        for contact in self.contacts_table.contacts_table:
            try:
                self.delete_contact(contact)
            except NotImplementedError:
                pass

        try:
            # Now remove the table itself
            self.contacts_table.remove_group(
                where="/{}/{}/{}".format(self.subject_id, self.session_id, self.measurement_id),
                name="contacts",
                recursive=True)
        except table.NoSuchNodeError:
            # If its already gone, we can just continue
            pass

        # And create it again
        self.contacts_table = table.ContactsTable(table=self.table,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)


    def delete_contact(self, contact):
        self.contacts_table.remove_row(table=self.contacts_table.contacts_table,
                                       name_id="contact_id",
                                       item_id=contact["contact_id"])
        self.contacts_table.remove_group(
            where="/{}/{}/{}".format(self.subject_id, self.session_id, self.measurement_id),
            name=contact["contact_id"],
            recursive=True)

    def get_contacts(self, plate, measurement):
        new_contacts = []
        measurement_id = measurement.measurement_id
        contact_data_table = table.ContactDataTable(table=self.table,
                                                    subject_id=self.subject_id,
                                                    session_id=self.session_id,
                                                    measurement_id=measurement_id)
        contacts_table = table.ContactsTable(table=self.table,
                                             subject_id=self.subject_id,
                                             session_id=self.session_id,
                                             measurement_id=measurement_id)
        # Get the rows from the table and their corresponding data
        contact_data = contact_data_table.get_contact_data()
        contacts = contacts_table.get_contacts()
        # Create Contact instances out of them
        for x, y in izip(contacts, contact_data):
            contact = Contact(subject_id=self.subject_id,
                              session_id=self.session_id,
                              measurement_id=self.measurement_id)
            # Restore it from the dictionary object
            # http://stackoverflow.com/questions/38987/how-can-i-merge-union-two-python-dictionaries-in-a-single-expression
            # This basically merges the two dicts into one
            contact.restore(dict(x, **y), plate=plate, measurement=measurement)
            new_contacts.append(contact)
        return new_contacts

    def repeat_track_contacts(self, measurement, measurement_data, plate):
        return self.track_contacts(measurement, measurement_data, plate)

    # @profile
    def track_contacts(self, measurement, measurement_data, plate):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        # Add padding to the measurement
        x = measurement.number_of_rows
        y = measurement.number_of_columns
        z = measurement.number_of_frames
        padding_factor = settings.settings.padding_factor()
        data = np.zeros((x + 2 * padding_factor, y + 2 * padding_factor, z), np.float32)
        data[padding_factor:-padding_factor, padding_factor:-padding_factor, :] = measurement_data
        raw_contacts = tracking.track_contours_graph(data)

        contacts = []
        # Convert them to class objects
        for index, raw_contact in enumerate(raw_contacts):
            contact = Contact(subject_id=self.subject_id,
                              session_id=self.session_id,
                              measurement_id=self.measurement_id)
            contact.create_contact(contact=raw_contact,
                                   measurement_data=measurement_data,
                                   orientation=measurement.orientation)
            contact.calculate_results(plate=plate, measurement=measurement)
            # Skip contacts that have only been around for one frame
            if contact.length > 1:
                contacts.append(contact)

        # Sort the contacts based on their position along the first dimension
        contacts = sorted(contacts, key=lambda contact: contact.min_z)
        # We don't calculate the spatiotemporal results, because there are no labels yet to do so

        # Update their index
        for contact_id, contact in enumerate(contacts):
            contact.contact_id = "contact_{}".format(contact_id)
        return contacts

    def verify_contacts(self, contacts):
        """
        Returns True if the contacts are up to date, returns False else
        """
        if not contacts:
            return False

        if all([contacts[0].stance_duration == np.nan, contacts[0].gait_velocity == np.nan]):
            return True
        return False

    def recalculate_results(self, contacts, plate, measurement, measurement_data):
        """
        We'll recalculate all the results except for the tracking or labeling
        """
        for contact in contacts:
            # Backup some values we want to keep
            backup = {"contact_id": contact.contact_id,
                      "contact_label": contact.contact_label,
                      "invalid": contact.invalid}

            contact.calculate_results(plate, measurement)
            contact.validate_contact(measurement_data)

            for key, value in backup.items():
                setattr(contact, key, value)

        contacts = self.calculate_multi_contact_results(contacts, plate, measurement)

        return contacts

    def get_contact_data(self, measurement):
        measurement_id = measurement.measurement_id
        contact_data_table = table.ContactDataTable(table=self.table,
                                                    subject_id=self.subject_id,
                                                    session_id=self.session_id,
                                                    measurement_id=measurement_id)

        # Get the rows from the table and their corresponding data
        return contact_data_table.get_contact_data()

    def calculate_multi_contact_results(self, contacts, plate, measurement):
        """
        These calculations have require contacts to be compared with one another and can't be performed on single
        contacts.
        """

        other_contact_lookup = {
            0: {"stride": 0, "step": 2, "ipsi": 1, "diag": 3},
            1: {"stride": 1, "step": 3, "ipsi": 0, "diag": 2},
            2: {"stride": 2, "step": 0, "ipsi": 3, "diag": 1},
            3: {"stride": 3, "step": 1, "ipsi": 2, "diag": 0},
        }

        # These results require multiple contacts...
        distances, label_lookup = calculations.temporal_spatial(contacts,
                                                                plate.sensor_width, plate.sensor_height,
                                                                measurement.frequency)
        for index, contact in enumerate(contacts):
            print index, contact.contact_id, id(contact)
            distance = distances[index]
            contact_label = contact.contact_label
            contact.gait_velocity = calculations.gait_velocity(contacts, distances)
            pattern = "-".join([str(contact.contact_label) for contact in contacts])
            contact.gait_pattern = calculations.find_gait_pattern(pattern=pattern)

            if contact_label < 0:
                continue

            stride_label = other_contact_lookup[contact_label]["stride"]
            stride_contact = distance.get(stride_label)
            if stride_contact:
                stride_duration = distance[contact_label][-1]
                contact.swing_duration = stride_duration - contact.stance_duration
                contact.stance_percentage = (contact.stance_duration * 100.) / stride_duration
                contact.stride_width = stride_contact[0]
                contact.stride_length = stride_contact[1]
                contact.stride_duration = stride_contact[2]

            step_label = other_contact_lookup[contact_label]["step"]
            step_contact = distance.get(step_label)
            if step_contact:
                contact.step_width = step_contact[0]
                contact.step_length = step_contact[1]
                contact.step_duration = step_contact[2]

            ipsi_label = other_contact_lookup[contact_label]["ipsi"]
            ipsi_contact = distance.get(ipsi_label)
            if ipsi_contact:
                contact.ipsi_width = ipsi_contact[0]
                contact.ipsi_length = ipsi_contact[1]
                contact.ipsi_duration = ipsi_contact[2]

            diag_label = other_contact_lookup[contact_label]["diag"]
            diag_contact = distance.get(diag_label)
            if diag_contact:
                contact.diag_width = diag_contact[0]
                contact.diag_length = diag_contact[1]
                contact.diag_duration = diag_contact[2]

        return contacts


class Contact(object):
    """
    This class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. These are a contour_list that contains all the contours
    and the dimensions + center of the bounding box of the entire contact

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
    """

    def __init__(self, subject_id, session_id, measurement_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.contact_id = None
        self.invalid = False
        self.edge_contact = False
        self.unfinished_contact = False
        self.incomplete_contact = False
        self.orientation = False
        self.filtered = False  # This can be used to check if the contact should be filtered or not
        self.contact_label = -2  # Contacts are labeled as -2 by default, this means unlabeled
        self.contour_list = defaultdict(list)
        self.padding = settings.settings.padding_factor()
        # We'll initialize these values so they'll always have a default
        self.gait_pattern = ""
        self.stride_width = np.nan
        self.stride_length = np.nan
        self.stride_duration = np.nan
        self.stride_width = np.nan
        self.stride_length = np.nan
        self.stride_duration = np.nan
        self.step_width = np.nan
        self.step_length = np.nan
        self.step_duration = np.nan
        self.ipsi_width = np.nan
        self.ipsi_length = np.nan
        self.ipsi_duration = np.nan
        self.diag_width = np.nan
        self.diag_length = np.nan
        self.diag_duration = np.nan
        self.swing_duration = np.nan
        self.stance_percentage = np.nan
        self.gait_velocity = np.nan

        self.table_attributes = ["subject_id", "session_id", "measurement_id", "contact_id", "contact_label",
                                 "min_x", "max_x", "min_y", "max_y", "min_z", "max_z", "width", "height", "length",
                                 "invalid", "filtered", "edge_contact", "unfinished_contact", "incomplete_contact",
                                 "orientation", "vertical_impulse", "time_of_peak_force", "peak_force", "peak_pressure",
                                 "peak_surface",
                                 "gait_pattern", "gait_velocity", "stance_duration", "swing_duration",
                                 "stance_percentage",
                                 "stride_duration", "stride_length", "stride_width", "step_duration", "step_length",
                                 "step_width",
                                 "ipsi_duration", "ipsi_length", "ipsi_width", "diag_duration", "diag_length",
                                 "diag_width"]

        self.data_attributes = ["data", "force_over_time", "pixel_count_over_time", "surface_over_time",
                                "pressure_over_time",
                                "cop_x", "cop_y", "vcop_xy", "vcop_x", "vcop_y", "max_of_max"]

    def create_contact(self, contact, measurement_data, orientation):
        self.orientation = orientation  # True means the contact is upside down
        frames = sorted(contact.keys())
        for frame in frames:
            # Adjust the contour for the padding
            contours = contact[frame]
            self.contour_list[frame] = []
            for contour in contours:
                if self.padding:
                    new_contour = []
                    for p in contour:
                        new_contour.append([[p[0][0] - self.padding, p[0][1] - self.padding]])
                    contour = np.array(new_contour)
                self.contour_list[frame].append(contour)

        _, min_x, max_x, min_y, max_y = utility.update_bounding_box(contact)
        # Subtract the amount of padding everywhere
        if self.padding:
            min_x -= self.padding
            max_x -= self.padding
            min_y -= self.padding
            max_y -= self.padding
        self.width = int(abs(max_x - min_x))
        self.height = int(abs(max_y - min_y))
        self.length = len(frames)
        self.min_x, self.max_x = int(min_x), int(max_x)
        self.min_y, self.max_y = int(min_y), int(max_y)
        self.min_z, self.max_z = frames[0], frames[-1]

        # Create self.measurement_data from the measurement_data
        self.convert_contour_to_slice(measurement_data)
        # Check if the contact is valid
        self.validate_contact(measurement_data)
        # If the contact is upside down, fix that
        if orientation:
            self.data = np.rot90(np.rot90(self.data))

    # @profile
    def convert_contour_to_slice(self, measurement_data):
        """
        Creates self.measurement_data which contains the pixels that are enclosed by the contour
        """
        # Create an empty array that should fit the entire contact
        self.data = np.zeros((self.width, self.height, self.length))

        for index, (frame, contours) in enumerate(sorted(self.contour_list.iteritems())):
            # Pass a single contour as if it were a contact
            center, min_x, max_x, min_y, max_y = utility.update_bounding_box({frame: contours})
            # Get the non_zero pixels coordinates for that frame
            pixels = np.transpose(np.nonzero(measurement_data[min_x:max_x + 1, min_y:max_y + 1, frame]))
            # Check if they are in any of the contours
            for pixel in pixels:
                for contour in contours:
                    # Remember the coordinates are only for the slice, so we need to add padding
                    coordinate = (min_x + pixel[0], min_y + pixel[1])
                    if cv2.pointPolygonTest(contour, coordinate, 0) > -1.0:
                        self.data[coordinate[0] - self.min_x, coordinate[1] - self.min_y, index] = measurement_data[
                            coordinate[0], coordinate[1], frame]

    def calculate_results(self, plate, measurement):
        """
        This function will calculate all the required results and store them in the contact object
        """
        # These assignments are all unnecessary
        self.force_over_time = calculations.force_over_time(self)
        self.pixel_count_over_time = calculations.pixel_count_over_time(self)
        self.pressure_over_time = calculations.pressure_over_time(self, sensor_surface=plate.sensor_surface)
        self.surface_over_time = calculations.surface_over_time(self, sensor_surface=plate.sensor_surface)
        self.cop_x, self.cop_y = calculations.calculate_cop(self)
        self.vcop_xy, self.vcop_x, self.vcop_y = calculations.velocity_of_cop(self, plate.sensor_width,
                                                                              plate.sensor_height,
                                                                              measurement.frequency)
        self.time_of_peak_force = calculations.time_of_peak_force(self, frequency=measurement.frequency,
                                                                  relative=False)
        # Note vertical impluse is NOT normalized here!
        self.vertical_impulse = calculations.vertical_impulse(self, frequency=measurement.frequency,
                                                              mass=1.0, version=2)
        self.max_of_max = np.max(self.data, axis=2)

        self.stance_duration = calculations.stance_duration(self, frequency=measurement.frequency)

        self.peak_force = calculations.peak_force(self)
        self.peak_pressure = calculations.peak_pressure(self, plate.sensor_surface)
        self.peak_surface = calculations.peak_surface(self, plate.sensor_surface)



    def validate_contact(self, measurement_data):
        """
        Input: measurement_data = 3D entire plate measurement_data array
        Checks if the contact touches the edge of the plate and if the forces at the beginning or end of a contact
        aren't too high. If so, it will mark the contact as invalid
        """
        self.edge_contact = False
        self.unfinished_contact = False
        self.incomplete_contact = False

        if self.touches_edge(measurement_data):
            self.edge_contact = True
        if self.incomplete_step():
            self.incomplete_contact = True
        if self.unfinished(measurement_data):
            self.unfinished_contact = True

        if self.edge_contact or self.unfinished_contact:
            self.invalid = True
            self.filtered = True

    def touches_edge(self, data):
        """
        Checks if the x, y and z dimensions don't hit the outer dimensions of the plate.
        Could be refined to require multiple sensors to touch the edge in order to invalidate a contact.
        """
        ny, nx, nt = data.shape
        x_touch = (self.min_x == 0) or (self.max_x == ny)
        y_touch = (self.min_y == 0) or (self.max_y == nx)
        return x_touch or y_touch

    def unfinished(self, data):
        ny, nx, nt = data.shape
        return self.max_z >= (nt - 1)

    def incomplete_step(self):
        """
        Checks if the force at the start or end of a contact aren't higher than a configurable threshold, in which case
        its likely the measurement didn't start fast enough or the measurement ended prematurely.
        """
        # force_over_time as an attribute is not yet available when this function is called
        force_over_time = calculations.force_over_time(self)
        max_force = np.max(force_over_time)
        if (force_over_time[0] > (settings.settings.start_force_percentage() * max_force) or
                    force_over_time[-1] > (settings.settings.end_force_percentage() * max_force)):
            return True
        return False

    # TODO This should be converted to a @classmethod
    # http://scipy-lectures.github.io/advanced/advanced_python/#id11
    def restore(self, contact, plate, measurement):
        """
        This function takes a dictionary of the stored_results (the result of contact_to_dict) and recreates all the
        attributes.
        """
        for key, value in contact.items():
            setattr(self, key, value)

        #self.calculate_results(plate=plate, measurement=measurement)


    def to_dict(self):
        # TODO convert this to a list of strings and a bunch of getattr calls
        return {
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "measurement_id": self.measurement_id,
            "contact_id": self.contact_id,
            "contact_label": self.contact_label,
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "min_z": self.min_z,
            "max_z": self.max_z,
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "invalid": self.invalid,
            "filtered": self.filtered,
            "edge_contact": self.edge_contact,
            "unfinished_contact": self.unfinished_contact,
            "incomplete_contact": self.incomplete_contact,
            "orientation": self.orientation,
            "vertical_impulse": self.vertical_impulse,
            "time_of_peak_force": self.time_of_peak_force,
            "peak_force": self.peak_force,
            "peak_pressure": self.peak_pressure,
            "peak_surface": self.peak_surface,
            "gait_pattern": self.gait_pattern,
            "gait_velocity": self.gait_velocity,
            "stance_duration": self.stance_duration,
            "swing_duration": self.swing_duration,
            "stance_percentage": self.stance_percentage,
            "stride_duration": self.stride_duration,
            "stride_length": self.stride_length,
            "stride_width": self.stride_width,
            "step_duration": self.step_duration,
            "step_length": self.step_length,
            "step_width": self.step_width,
            "ipsi_duration": self.ipsi_duration,
            "ipsi_length": self.ipsi_length,
            "ipsi_width": self.ipsi_width,
            "diag_duration": self.diag_duration,
            "diag_length": self.diag_length,
            "diag_width": self.diag_width,
        }


class MockContacts(Contacts):
    def __init__(self, subject_id, session_id, measurement_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id


class MockContact(Contact):
    def __init__(self, contact_id, data):
        self.contact_id = contact_id
        subject_id = "subject_1"
        session_id = "session_1"
        measurement_id = "measurement_1"
        self.data = data
        super(MockContact, self).__init__(subject_id, session_id, measurement_id)