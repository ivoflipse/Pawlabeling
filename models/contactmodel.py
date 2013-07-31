from collections import defaultdict
import numpy as np
from settings import configuration
from functions import io, tracking, utility, calculations
from functions.pubsub import pub
import logging
import cv2

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
        self.center = (0, 0)
        self.width = 1
        self.height = 1
        self.length = 1
        self.contour_list = defaultdict(list)
        self.frames = []
        self.data = np.zeros((self.max_x, self.max_y, self.max_z))
        self.invalid = False
        self.paw_label = -2  # Paws are labeled as -2 by default

    def create_contact(self, contact, padding=0):
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

        center, min_x, max_x, min_y, max_y = self.update_bounding_box(contact)
        # Subtract the amount of padding everywhere
        if padding:
            min_x -= padding
            max_x -= padding
            min_y -= padding
            max_y -= padding
            center = (center[0] - padding, center[1] - padding)
        self.width = int(abs(max_x - min_x))
        self.height = int(abs(max_y - min_y))
        self.length = len(self.frames)
        self.min_x, self.max_x = int(min_x), int(max_x)
        self.min_y, self.max_y = int(min_y), int(max_y)
        self.min_z, self.max_z = self.frames[0], self.frames[-1]
        self.center = (int(center[0]), int(center[1]))

    def convert_contour_to_slice(self, data):
        """
        Creates self.data which contains the pixels that are enclosed by the contour
        """
        # Create an empty array that should fit the entire contact
        new_data = np.zeros_like(data)

        for frame, contours in list(self.contour_list.items()):
            skip_list = []
            for contour in contours:
                # Pass a single contour as if it were a contact
                center, min_x, max_x, min_y, max_y = self.update_bounding_box({frame: contour})
                # Get the non_zero pixels coordinates for that frame
                pixels = np.transpose(np.nonzero(data[min_x:max_x, min_y:max_y, frame]))
                for pixel in pixels:
                    # Skip pixels we already did in this frame
                    if pixel not in skip_list:
                        if cv2.pointPolygonTest(contour, pixel, 0) > -1.0:
                            new_data[pixel[0], pixel[1], frame] = data[pixel[0], pixel[1], frame]
                            skip_list.append(pixel)

        # Create an attribute data with the updated slice
        self.data = new_data[self.min_x:self.max_x, self.min_y:self.max_y,self.min_z:self.max_z]

    def update_bounding_box(self, contact):
        """
        This function will iterate through all the frames and calculate the bounding box
        It then compares the dimensions of the bounding box to determine the total shape of that
        contacts bounding box
        """
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        # For each contour, get the sizes
        for frame, contours in contact.items():
            for contour in contours:
                x, y, width, height = cv2.boundingRect(contour)
                if x < min_x:
                    min_x = x
                max_x = x + width
                if max_x > max_x:
                    max_x = max_x
                if y < min_y:
                    min_y = y
                max_y = y + height
                if max_y > max_y:
                    max_y = max_y

        total_centroid = ((max_x + min_x) / 2, (max_y + min_y) / 2)
        return total_centroid, min_x, max_x, min_y, max_y

    def validate_contact(self, data):
        if self.touches_edge(data) or self.incomplete_step():
            self.invalid = True
            self.paw_label = -3

    def touches_edge(self, data):
        ny, nx, nt = data.shape
        x_touch = (self.min_x == 0) or (self.max_x == ny)
        y_touch = (self.min_y == 0) or (self.max_y == nx)
        z_touch = (self.min_z == nt)

        return x_touch or y_touch or z_touch

    def incomplete_step(self):
        force_over_time = calculations.force_over_time(self.data)
        max_force = np.max(force_over_time)
        if (force_over_time[0] > (configuration.start_force_percentage * max_force) or
                    force_over_time[-1] > (configuration.end_force_percentage * max_force)):
            return True
        return False

    def restore(self, contact):
        self.contour_list = {} # I can't really be bothered to reconstruct this
        self.frames = [x for x in range(contact["min_z"], contact["max_z"] + 1)]
        self.width = contact["width"]
        self.height = contact["height"]
        self.length = contact["length"]
        self.min_x = contact["min_x"]
        self.max_x = contact["max_x"]
        self.min_y = contact["min_y"]
        self.max_y = contact["max_y"]
        self.center = (contact["center_x"], contact["center_y"])

    def contact_to_dict(self):
        # TODO make this and restore up to date!
        return {
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "min_z": self.frames[0],
            "max_z": self.frames[-1],
            "center_x": self.center[0],
            "center_y": self.center[1]
        }
