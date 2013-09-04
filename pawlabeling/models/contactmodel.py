from collections import defaultdict
import logging
import numpy as np
import cv2
from pawlabeling.functions import utility, calculations
from pawlabeling.settings import configuration
#from memory_profiler import profile

logger = logging.getLogger("logger")


class Contact():
    """
    This class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. These are a contour_list that contains all the contours
    and the dimensions + center of the bounding box of the entire contact
    """

    def __init__(self):
        # I hope this won't get me into trouble if for whatever reason its not updated
        self.min_x = 0
        self.max_x = 1
        self.min_y = 0
        self.max_y = 1
        self.min_z = 0
        self.max_z = 1
        self.width = 1
        self.height = 1
        self.length = 1
        self.contour_list = defaultdict(list)
        self.frames = []
        self.data = np.zeros((self.max_x, self.max_y, self.max_z))
        self.max_of_max = np.zeros((self.max_x, self.max_y))
        self.invalid = False
        self.filtered = False  # This can be used to check if the contact should be filtered or not
        self.contact_label = -2  # contacts are labeled as -2 by default
        self.orientation = False  # True means the contact is upside down

    def create_contact(self, contact, measurement_data, padding=0, orientation=False):
        """
        This function expects a contact object, which is a dictionary of frames:list of contours and a padding value
        It will remove the padding from the contours and calculate the dimensions of a bounding box
        """
        self.frames = sorted(contact.keys())
        self.contour_list = {}
        for frame in self.frames:
            # Adjust the contour for the padding
            contours = contact[frame]
            self.contour_list[frame] = []
            for contour in contours:
                if padding:
                    new_contour = []
                    for p in contour:
                        new_contour.append([[p[0][0] - padding, p[0][1] - padding]])
                    contour = np.array(new_contour)
                self.contour_list[frame].append(contour)

        _, min_x, max_x, min_y, max_y = utility.update_bounding_box(contact)
        # Subtract the amount of padding everywhere
        if padding:
            min_x -= padding
            max_x -= padding
            min_y -= padding
            max_y -= padding
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
        # Calculate the results
        self.calculate_results()

    #@profile
    def convert_contour_to_slice(self, measurement_data):
        """
        Creates self.measurement_data which contains the pixels that are enclosed by the contour
        """
        # Create an empty array that should fit the entire contact
        self.data = np.zeros((self.width, self.height, self.length))


        for index, (frame, contours) in enumerate(sorted(self.contour_list.items())):
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
                        self.data[coordinate[0]-self.min_x, coordinate[1]-self.min_y, index] = measurement_data[
                            coordinate[0], coordinate[1], frame]

    def calculate_results(self):
        """
        This function will calculate all the required results and store them in the contact object
        """
        self.force_over_time = calculations.force_over_time(self.data)
        self.pressure_over_time = calculations.pressure_over_time(self.data)
        self.surface_over_time = calculations.surface_over_time(self.data)
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
        if self.touches_edge(measurement_data) or self.incomplete_step():
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

        return x_touch or y_touch or z_touch

    def incomplete_step(self):
        """
        Checks if the force at the start or end of a contact aren't higher than a configurable threshold, in which case
        its likely the measurement didn't start fast enough or the measurement ended prematurely.
        """
        force_over_time = calculations.force_over_time(self.data)
        max_force = np.max(force_over_time)
        #print force_over_time[0], force_over_time[-1], max_force, configuration.start_force_percentage
        if (force_over_time[0] > (configuration.start_force_percentage * max_force) or
                    force_over_time[-1] > (configuration.end_force_percentage * max_force)):
            return True
        return False

    def restore(self, contact):
        """
        This function takes a dictionary of the stored_results (the result of contact_to_dict) and recreates all the
        attributes.
        """
        self.contact_id = int(contact["contact_id"].split("_")[1])  # Convert it back
        self.contact_label = contact["contact_label"]
        self.frames = [x for x in range(contact["min_z"], contact["max_z"] + 1)]
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
            "contact_id": "contact_{}".format(self.contact_id),
            "contact_label": self.contact_label,
            "data": self.data,
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
