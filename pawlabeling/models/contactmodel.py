from collections import defaultdict
import cv2
from itertools import izip

import numpy as np
from pubsub import pub

from pawlabeling.functions import utility, calculations, tracking
from pawlabeling.settings import settings
from pawlabeling.models import table

#from memory_profiler import profile


class Contacts(object):
    def __init__(self, subject_id, session_id, measurement_id):
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.contacts_table = table.ContactsTable(database_file=self.database_file,
                                                  subject_id=self.subject_id,
                                                  session_id=self.session_id,
                                                  measurement_id=self.measurement_id)

    def create_contacts(self, measurement, measurement_data, plate):
        """
        Create contacts works slightly different than the other models.
        track_contacts returns a list of list of Contact instances
        create_contact only takes care of the storing of the results in PyTables
        """
        contacts = self.track_contacts(measurement, measurement_data, plate)
        for contact in contacts:
            self.create_contact(contact)
        return contacts

    # TODO Really it actually should never happen that I have to call create_contact when it already exists!
    def create_contact(self, contact):
        # If the contact is already present, we update instead and return its ID
        update = False
        if self.contacts_table.get_contact(contact_id=contact.contact_id):
            update = True

        # We store the results separately
        results = {"data": contact.data,
                   "max_of_max": contact.max_of_max,
                   "force_over_time": contact.force_over_time,
                   "pressure_over_time": contact.pressure_over_time,
                   "surface_over_time": contact.surface_over_time,
                   "cop_x": contact.cop_x,
                   "cop_y": contact.cop_y
        }

        # Convert the contact to a dict, like the table expects
        contact = contact.to_dict()
        if update:
            self.contact_group = self.contacts_table.update_contact(**contact)
        else:
            # If it doesn't already exist, we create the contact and store the data
            self.contact_group = self.contacts_table.create_contact(**contact)

        for item_id, data in results.iteritems():
            result = self.contacts_table.get_data(group=self.contact_group, item_id=item_id)
            if not result:
                self.contacts_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)
                # If the arrays are not equal, drop the old one and write the new data
            elif not np.array_equal(result, data):
                # TODO I can't really test this this without changing my tracking
                print "Item: {} is not equal to the stored version".format(item_id)
                # Let's hope this will simply replace the old values
                # http://hdf-forum.184993.n3.nabble.com/hdf-forum-Reset-data-in-pytables-array-td193311.html
                # Supposedly I should use arr.__set__item(key, value)
                # But I reckon that assumes the shapes stay the same
                self.contacts_table.store_data(group=self.contact_group,
                                               item_id=item_id,
                                               data=data)

    def get_contacts(self, measurement):
        new_contacts = []
        measurement_id = measurement.measurement_id
        contact_data_table = table.ContactDataTable(database_file=self.database_file,
                                                    subject_id=self.subject_id,
                                                    session_id=self.session_id,
                                                    measurement_id=measurement_id)
        contacts_table = table.ContactsTable(database_file=self.database_file,
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
            contact.restore(dict(x, **y))  # This basically merges the two dicts into one
            new_contacts.append(contact)
        return new_contacts

    def repeat_track_contacts(self, measurement, measurement_data, plate):
        return self.track_contacts(measurement, measurement_data, plate)

    #@profile
    def track_contacts(self, measurement, measurement_data, plate):
        pub.sendMessage("update_statusbar", status="Starting tracking")
        # Add padding to the measurement
        x = measurement.number_of_rows
        y = measurement.number_of_columns
        z = measurement.number_of_frames
        padding_factor = self.settings.padding_factor()
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
            contact.calculate_results(sensor_surface=plate.sensor_surface)
            # Skip contacts that have only been around for one frame
            if len(contact.frames) > 1:
                contacts.append(contact)

        # Sort the contacts based on their position along the first dimension
        contacts = sorted(contacts, key=lambda contact: contact.min_z)
        # Update their index
        for contact_id, contact in enumerate(contacts):
            contact.set_contact_id(contact_id)
        return contacts

    def update_contact(self, contact):
        self.contacts_table.update_contact(**contact)

    def update_contacts(self, contacts, measurement_name):
        for contact in contacts[measurement_name]:
            contact = contact.to_dict()  # This takes care of some of the book keeping for us
            self.update_contact(contact)
        self.contacts_table.contacts_table.flush()

    def get_contact_data(self, measurement):
        measurement_id = measurement.measurement_id
        contact_data_table = table.ContactDataTable(database_file=self.database_file,
                                                    subject_id=self.subject_id,
                                                    session_id=self.session_id,
                                                    measurement_id=measurement_id)

        # Get the rows from the table and their corresponding data
        return contact_data_table.get_contact_data()


class Contact(object):
    """
    This class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. These are a contour_list that contains all the contours
    and the dimensions + center of the bounding box of the entire contact
    """

    def __init__(self, subject_id, session_id, measurement_id, ):
        self.subject_id = subject_id
        self.session_id = session_id
        self.measurement_id = measurement_id
        self.contact_id = None
        self.invalid = False
        self.orientation = False
        self.filtered = False  # This can be used to check if the contact should be filtered or not
        self.contact_label = -2  # Contacts are labeled as -2 by default, this means unlabeled
        self.settings = settings.settings
        self.contour_list = defaultdict(list)
        self.padding = self.settings.padding_factor()
        self.frames = []

    def create_contact(self, contact, measurement_data, orientation):
        self.orientation = orientation  # True means the contact is upside down
        self.frames = sorted(contact.keys())
        for frame in self.frames:
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
        self.length = len(self.frames)
        self.min_x, self.max_x = int(min_x), int(max_x)
        self.min_y, self.max_y = int(min_y), int(max_y)
        self.min_z, self.max_z = self.frames[0], self.frames[-1]

        # Create self.measurement_data from the measurement_data
        self.convert_contour_to_slice(measurement_data)
        # Check if the contact is valid
        self.validate_contact(measurement_data)
        # If the contact is upside down, fix that
        if orientation:
            self.data = np.rot90(np.rot90(self.data))

    #@profile
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

    def calculate_results(self, sensor_surface):
        """
        This function will calculate all the required results and store them in the contact object
        """
        self.force_over_time = calculations.force_over_time(self.data)
        self.pressure_over_time = calculations.pressure_over_time(self.data, sensor_surface=sensor_surface)
        self.surface_over_time = calculations.surface_over_time(self.data, sensor_surface=sensor_surface)
        self.cop_x, self.cop_y = calculations.calculate_cop(self.data)
        self.max_of_max = np.max(self.data, axis=2)

    def set_orientation(self, orientation):
        """
        If a contact is upside down, we set this boolean flag, so we can rotate it when we need to calculate averages
        """
        self.orientation = orientation

    def set_filtered(self, filtered):
        """
        If a contact deviates too many standard deviations from the rest of the contacts, you can set it to filtered
        which can be accessed by the results widgets to see if they should ignore it
        """
        self.filtered = filtered

    def set_contact_label(self, contact_label):
        """
        Lets you set the contact_label. Only used, so I can log when/where this happens for bug tracking purposes.
        """
        self.contact_label = contact_label

    def set_contact_id(self, contact_id):
        """
        Lets you set the contact_id. Only used, so I can log when/where this happens for bug tracking purposes.
        """
        self.contact_id = contact_id

    def validate_contact(self, measurement_data):
        """
        Input: measurement_data = 3D entire plate measurement_data array
        Checks if the contact touches the edge of the plate and if the forces at the beginning or end of a contact
        aren't too high. If so, it will mark the contact as invalid and set the contact_label to -3
        """
        if self.touches_edge(measurement_data) or self.incomplete_step:
            self.invalid = True
            self.contact_label = -3

    def touches_edge(self, data):
        """
        Checks if the x, y and z dimensions don't hit the outer dimensions of the plate.
        Could be refined to require multiple sensors to touch the edge in order to invalidate a contact.
        """
        ny, nx, nt = data.shape
        x_touch = (self.min_x == 0) or (self.max_x == ny)
        y_touch = (self.min_y == 0) or (self.max_y == nx)
        z_touch = (self.min_z == nt)
        #print x_touch, y_touch, z_touch
        return x_touch or y_touch or z_touch

    @property
    def incomplete_step(self):
        """
        Checks if the force at the start or end of a contact aren't higher than a configurable threshold, in which case
        its likely the measurement didn't start fast enough or the measurement ended prematurely.
        """
        force_over_time = calculations.force_over_time(self.data)
        max_force = np.max(force_over_time)
        #print force_over_time[0], force_over_time[-1], max_force, self.settings.start_force_percentage()
        if (force_over_time[0] > (self.settings.start_force_percentage() * max_force) or
                    force_over_time[-1] > (self.settings.end_force_percentage() * max_force)):
            return True
        return False

    # TODO This should be converted to a @classmethod
    # http://scipy-lectures.github.io/advanced/advanced_python/#id11
    def restore(self, contact):
        """
        This function takes a dictionary of the stored_results (the result of contact_to_dict) and recreates all the
        attributes.
        """
        self.subject_id = contact["subject_id"]
        self.session_id = contact["session_id"]
        self.measurement_id = contact["measurement_id"]
        self.contact_id = int(contact["contact_id"].split("_")[1])  # Convert it back
        self.contact_label = contact["contact_label"]
        self.frames = [x for x in xrange(contact["min_z"], contact["max_z"] + 1)]
        self.width = contact["width"]
        self.height = contact["height"]
        self.length = contact["length"]
        self.min_x = contact["min_x"]
        self.max_x = contact["max_x"]
        self.min_y = contact["min_y"]
        self.max_y = contact["max_y"]
        self.min_z = contact["min_z"]
        self.max_z = contact["max_z"]
        self.invalid = contact["invalid"]
        self.filtered = contact["filtered"]
        self.orientation = contact["orientation"]
        self.data = contact["data"]
        self.force_over_time = contact["force_over_time"]
        self.pressure_over_time = contact["pressure_over_time"]
        self.surface_over_time = contact["surface_over_time"]
        self.cop_x = contact["cop_x"]
        self.cop_y = contact["cop_y"]
        self.max_of_max = contact["max_of_max"]

    def to_dict(self):
        return {
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "measurement_id": self.measurement_id,
            "contact_id": "contact_{}".format(self.contact_id),
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
            "orientation": self.orientation
        }
