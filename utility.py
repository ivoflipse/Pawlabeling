#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PySide.QtCore import *
from PySide.QtGui import *
import numpy as np
from settings import configuration

class Contact():
    """
    This class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. These are a contour_list that contains all the contours
    and the dimensions + center of the bounding box of the entire contact
    """

    def __init__(self, contact, restoring=False):
        if not restoring:
            self.frames = sorted(contact.keys())
            self.contour_list = {}
            for frame in self.frames:
                self.contour_list[frame] = contact[frame]

            center, min_x, max_x, min_y, max_y = update_bounding_box(contact)
            self.width = int(abs(max_x - min_x))
            self.height = int(abs(max_y - min_y))
            self.length = len(self.frames)
            self.total_min_x, self.total_max_x = int(min_x), int(max_x)
            self.total_min_y, self.total_max_y = int(min_y), int(max_y)
            self.total_centroid = (int(center[0]), int(center[1]))
        else:
            self.restore(contact)

    def restore(self, contact):
        self.contour_list = {} # This will sadly not be reconstructed
        results = contact["paw_results"]
        self.frames = [x for x in range(results["min_z"], results["max_z"]+1)]
        self.width = results["width"]
        self.height = results["height"]
        self.length = results["length"]
        self.total_min_x = results["min_x"]
        self.total_max_x = results["max_x"]
        self.total_min_y = results["min_y"]
        self.total_max_y = results["max_y"]
        self.total_centroid = (results["center_x"], results["center_y"])

    def contact_to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "length": self.length,
            "min_x": self.total_min_x,
            "max_x": self.total_max_x,
            "min_y": self.total_min_y,
            "max_y": self.total_max_y,
            "min_z": self.frames[0],
            "max_z": self.frames[-1],
            "center_x": self.total_centroid[0],
            "center_y": self.total_centroid[1]
        }

    def __str__(self):
        for frame in self.frames:
            print("Frame %s", frame)
            for index, contour in enumerate(self.contour_list[frame]):
                print("Contour %s: %s" % (index, "".join([str(c) for c in contour])))


def calculate_bounding_box(contour):
    """
    This function calculates the bounding box based on an individual contour
    For this is uses OpenCV's area rectangle, which fits a rectangle around a
    contour. Depending on the 'angle' of the rectangle, I switch around the
    definition of the width and length, so it lines up with the orientation
    of the plate. By subtracting the halves of the center, we get the extremes.
    """
    # Calculate a minimum bounding rectangle, can be rotated!
    from cv2 import minAreaRect

    center, size, angle = minAreaRect(contour)
    if -45 <= angle <= 45:
        width, length = size
    else:
        length, width = size

    x, y = center
    xdist = width / 2
    ydist = length / 2
    # Calculate the distance from the center to the edges
    min_x = x - xdist
    max_x = x + xdist
    min_y = y - ydist
    max_y = y + ydist
    return center, min_x, max_x, min_y, max_y


def update_bounding_box(contact):
    """
    Given a contact, it will iterate through all the frames and calculate the bounding box
    It then compares the dimensions of the bounding box to determine the total shape of that
    contacts bounding box
    """
    # Don't accept empty contacts
    assert len(contact) > 0

    total_min_x, total_max_x = float("inf"), float("-inf")
    total_min_y, total_max_y = float("inf"), float("-inf")

    # For each contour, get the sizes
    for frame in list(contact.keys()):
        for contour in contact[frame]:
            center, min_x, max_x, min_y, max_y = calculate_bounding_box(contour)
            if min_x < total_min_x:
                total_min_x = min_x
            if max_x > total_max_x:
                total_max_x = max_x
            if min_y < total_min_y:
                total_min_y = min_y
            if max_y > total_max_y:
                total_max_y = max_y

    total_centroid = ((total_max_x + total_min_x) / 2, (total_max_y + total_min_y) / 2)
    return total_centroid, total_min_x, total_max_x, total_min_y, total_max_y


def closest_contact(contact1, contact2, center1, euclidean_distance):
    """
    We take all the frames, add some to bridge any gaps, then we calculate the distance
    between the center of the first (short) contact and center of the second contact
    in each frame. This assumes the first contact doesn't move a lot, while the
    the second (and often longer) contact might move closer to the first contact.
    For each frame where the distance between the two centers is closer than the
    euclidean distances, we subtract the distance from the ED, such that closer contacts
    get a higher value and increment the value for every frame the distance is short enough.
    In the end we regularize the value, to prevent it from growing too large and taking
    an earlier position in the heap.
    """
    # Perhaps I should add a boolean for when there's a gap or not
    frames = list(contact1.keys())
    minFrame, maxFrame = min(frames), max(frames)
    # This makes sure it checks if there's nothing close in the neighboring frame
    # Shouldn't this be up to the gap?
    # Add more frames
    for f in range(1, 6):
        frames.append(minFrame - f)
        frames.append(maxFrame + f)
        #frames += [minFrame - 2, minFrame - 1, maxFrame + 1, maxFrame + 2]
    minDistance = euclidean_distance
    value = 0
    for frame in frames:
        if frame in contact2:
            if contact2[frame]: # How can there be an empty list in here?
                center2, _, _, _, _ = update_bounding_box({frame: contact2[frame]})
                #distance = np.linalg.norm(np.array(center1) - np.array(center2))
                x1 = center1[0]
                y1 = center1[1]
                x2 = center2[0]
                y2 = center2[1]
                distance = (abs(x1 - x2) ** 2 + abs(y1 - y2) ** 2) ** 0.5
                if distance < minDistance:
                    minDistance = distance
                if distance <= euclidean_distance:
                    value += euclidean_distance - distance
    return value / float(len(frames))


def calculate_temporal_spatial_variables(contacts):
    """
    We recalculate the euclidean distance based on the current size of the  remaining contacts
    This ensures that we reduce the number of false positives, by having a too large euclidean distance
    It assumes contacts are more of less round, such that the width and height are equal.
    """
    sides = []
    centers = []
    surfaces = []
    lengths = []
    for contact in contacts:
        # Get the dimensions for each contact
        center, min_x, max_x, min_y, max_y = update_bounding_box(contact)
        centers.append(center)

        width = max_x - min_x
        if width > 2:
            sides.append(width)
        height = max_y - min_y
        if height > 2:
            sides.append(height)

        surface = width * height
        surfaces.append(surface)

        lengths.append(len(list(contact.keys())))
    return sides, centers, surfaces, lengths


def merge_contours(contact1, contact2):
    """
    This function takes two contacts, then for each frame the second was active,
    add its contours to the first, then clears the second just to be safe
    """
    # Iterate through all the frames
    for frame in contact2:
        if frame not in contact1:
            contact1[frame] = []
        for contour in contact2[frame]:
            contact1[frame].append(contour)
            # This makes sure it won't accidentally merge either
        contact2[frame] = []


def merging_contacts(contacts):
    """
    We compare each contact with the rest, if the distance between the centers of both
    contacts is <= the euclidean distance, then we check if they also made contact during the
    same frames. This ensures that only contours that are in each others vicinity for a sufficient
    amount of frames are considered for merging. Just naively merging based on distance would
    cause problems if dogs place the paws too close too each other.
    This will fail if the dogs paws are close for more frames than the threshold.
    """
    import heapq

    # Get the important temporal spatial variables
    sides, centerList, surfaces, lengths = calculate_temporal_spatial_variables(contacts)
    # Get their averages and adjust them when needed
    frame_threshold = np.mean(lengths) * 0.5
    euclideanDistance = np.mean(sides)
    averageSurface = np.mean(surfaces) * 0.25
    # Initialize two dictionaries for calculating the Minimal Spanning Tree
    leaders = {}
    clusters = {}
    # This list forms the heap to which we'll add all edges
    edges = []
    for index1, contact1 in enumerate(contacts):
        clusters[index1] = {index1}
        leaders[index1] = index1

        center1 = centerList[index1]
        frames1 = set(contact1.keys())
        length1 = len(frames1)
        surface1 = surfaces[index1]
        for index2, contact2 in enumerate(contacts):
            if index1 != index2:
                center2 = centerList[index2]
                #distance = np.linalg.norm(np.array(center1) - np.array(center2))
                # Instead of linalg, we just compare the first two coordinates
                # of both contacts
                x1 = center1[0]
                y1 = center1[1]
                x2 = center2[0]
                y2 = center2[1]
                distance = (abs(x1 - x2) ** 2 + abs(y1 - y2) ** 2) ** 0.5
                # We only check for merges if the distance between the two contacts
                # is less than the euclidean distance
                if distance <= euclideanDistance:
                    frames2 = set(contact2.keys())
                    #length2 = len(frames2)
                    # Calculate how many frames of overlap there is between two contacts
                    overlap = len(list(frames1 & frames2))
                    ratio = overlap / float(length1)

                    merge = False
                    value = None
                    if overlap:
                        # We have 4 different cases where contacts can be merged
                        # If the overlap is larger than the frame_threshold we always merge
                        if overlap >= frame_threshold:
                            merge = True
                            value = (euclideanDistance - distance) * overlap
                        # If the first contact is too short, but we have overlap nonetheless,
                        # we also merge, we'll deal with picking the best value later
                        elif length1 <= frame_threshold and overlap:
                            merge = True
                        # Some contacts are longer than the threshold, yet don't have overlap
                        # that's larger than the threshold. However, because the overlap is
                        # significant, we'll allow it to merge too
                        elif ratio >= 0.5:
                            merge = True
                        # This deals with the edge cases where a contact is really small
                        # yet because its duration is quite long, it wouldn't get merged
                        elif ratio >= 0.2 and surface1 < averageSurface:
                            merge = True
                    # In some cases we don't get a merge because there's no overlap
                    # But still its clear these pixels belong to a paw in adjacent frames
                    # If the gap between the two contacts isn't too large, we'll allow that one too
                    else:
                        if length1 <= frame_threshold and not overlap:
                            gap = min([abs(f1 - f2) for f1 in frames1 for f2 in frames2])
                            if gap < 5: # I changed it to 5, which may or may not work
                                merge = True
                                # If we've found a merge, we'll add it to the heap
                    if merge:
                    # We use two different values for large and short contacts
                        # here we check whether we should calculate a different value
                        if not value:
                            # For short contacts we calculate the average distance to the contact
                            # Which seems to be much more reliable, yet is computationally more expensive
                            value = closest_contact(contact1, contact2, center1, euclideanDistance)
                            # Use a heap to get the minimum item
                        heapq.heappush(edges, (-value, index1, index2))

    explored = set()
    # While we have edges left in the heap or we've explored all contacts
    while edges and len(explored) != len(contacts):
        # Get an edge from the heap
        value, index1, index2 = heapq.heappop(edges)
        leader1 = leaders[index1]
        leader2 = leaders[index2]
        # Check if the label of the two contacts isn't equal and the
        # first contact hasn't been explored yet.
        if leader1 != leader2 and index1 not in explored:
            explored.add(index1)
            # Find the shortest one, so we have to do less work
            if len(contacts[leader1]) <= len(contacts[leader2]):
                min_cluster, max_cluster = leader1, leader2
            else:
                min_cluster, max_cluster = leader2, leader1
                # Merge the two contacts, so delete the nodes
            # that are part of the short cluster
            # and add them to the large cluster
            for node in clusters[min_cluster]:
                # Add it to the cluster of the max_cluster
                clusters[max_cluster].add(node)
                # Replace its label
                leaders[node] = max_cluster
                if node in clusters:
                    # Delete the old cluster
                    del clusters[node]

    new_contacts = []
    # I defer merging till the end, because else
    # we might have to move things around several times
    # This is where we actually merge the contacts in
    # each cluster
    for key, indices in list(clusters.items()):
        newContact = {}
        for index in indices:
            contact = contacts[index]
            merge_contours(newContact, contact)
        new_contacts.append(newContact)

    return new_contacts


def find_contours(data):
    from cv2 import threshold, findContours, THRESH_BINARY, RETR_EXTERNAL, CHAIN_APPROX_NONE
    # Dictionary to fill with results
    contour_dict = {}
    # Find the contours in this frame
    rows, cols, numFrames = data.shape
    for frame in range(numFrames):
        # Threshold the data
        copy_data = data[:, :, frame].T * 1.
        _, copy_data = threshold(copy_data, 0.0, 1, THRESH_BINARY)
        # The astype conversion here is quite expensive!
        contour_list, _ = findContours(copy_data.astype('uint8'), RETR_EXTERNAL, CHAIN_APPROX_NONE)
        if contour_list:
            contour_dict[frame] = contour_list
    return contour_dict


def create_graph(contour_dict, euclideanDistance=15):
    from cv2 import pointPolygonTest
    # Create a graph
    G = {}
    # Now go through the contour_dict and for each contour, check if there's a matching contour in the adjacent frame
    for frame in contour_dict:
        contours = contour_dict[frame]
        for index1, contour1 in enumerate(contours):
            # Initialize a key for this frame + index combo
            G[(frame, index1)] = set()
            # Get the contours from the previous frame
            for f in [frame - 1]:
                if f in contour_dict:
                    otherContours = contour_dict[f]
                    # Iterate through the contacts in the adjacent frame
                    for index2, contour2 in enumerate(otherContours):
                        if (f, index2) not in G:
                            G[(f, index2)] = set()
                            # Pick the shortest contour, to do the least amount of work
                        if len(contour1) <= len(contour2):
                            short_contour, long_contour = contour1, contour2
                        else:
                            short_contour, long_contour = contour2, contour1

                        # Compare the first two coordinates, if they aren't even close. Don't bother
                        coord1 = short_contour[0]
                        coord2 = long_contour[0]
                        distance = coord1[0][0] - coord2[0][0]
                        # Taking a safe margin
                        if distance <= 2 * euclideanDistance:
                            match = False
                            # We iterate through all the coordinates in the short contour and test if
                            # they fall within or on the border of the larger contour. We stop comparing
                            # ones we've found a match
                            for coordinates in short_contour:
                                if not match:
                                    coordinates = (coordinates[0][0], coordinates[0][1])
                                    if pointPolygonTest(long_contour, coordinates, 0) > -1.0:
                                        match = True
                                        # Create a bi-directional edge between the two keys
                                        G[(frame, index1)].add((f, index2))
                                        G[(f, index2)].add((frame, index1))
                                        # Perhaps this could be sped up, by keeping a cache of centroids of paws
                                        # then check if there was a paw in the same place on the last frame
                                        # if so, link them and stop looking
    return G


def search_graph(G, contour_dict):
    # Empty list of contacts
    contacts = []
    # Set to keep track of contours we've already visited
    explored = set()
    # Go through all nodes in G and find every node
    # its connected to using BFS
    for key in G:
        if key not in explored:
            frame, index1 = key
            # Initialize a new contact
            contact = {frame: [contour_dict[frame][index1]]}
            #contact[frame] = [contour_dict[frame][index1]]
            explored.add(key)
            nodes = set(G[key])
            # Keep going until there are no more nodes to explore
            while len(nodes) != 0:
                vertex = nodes.pop()
                if vertex not in explored:
                    f, index2 = vertex
                    if f not in contact:
                        contact[f] = []
                    contact[f].append(contour_dict[f][index2])
                    # Add vertex's neighbors to nodes
                    for v in G[vertex]:
                        if v not in explored:
                            nodes.add(v)
                    explored.add(vertex)
                    # When we're done add the contact to the contacts list
            contacts.append(contact)
    return contacts


def track_contours_graph(data):
    """
    This tracking algorithm uses a graph based approach.
    It finds all the contours in each frame, connects them based on whether
    they have overlap in adjacent frames. Then finds connected components
    using a simple graph search. These resulting connected components might
    be unconnected, yet part of the same contact. So we calculate two threshold
    based on the average duration and width/height of the connected components.
    These are then used to merge connected components with sufficient overlap.
    """
    # Find all the contours, put them in a dictionary where the keys are the frames
    # and the values are the contours
    contour_dict = find_contours(data)
    # Create a graph by connecting contours that have overlap with contours in the
    # previous frame
    G = create_graph(contour_dict, euclideanDistance=15)
    # Search through the graph for all connected components
    contacts = search_graph(G, contour_dict)
    # Merge connected components using a minimal spanning tree, where
    # the contacts larger than the threshold are only allowed to merge if they
    # have overlap that's >= than the frame threshold
    contacts = merging_contacts(contacts)
    return contacts


def standardize_paw(paw, std_num_x=20, std_num_y=20):
    """Standardizes a paw print onto a std_num_y x std_num_x grid. Returns a 1D,
    flattened version of the paw data resample onto this grid."""
    from scipy.ndimage import map_coordinates

    ny, nx = np.shape(paw)
    # Based on a scientific guess
    # Make a 20x20 grid to resample the paw pressure values onto
    #std_num_x, std_num_y = 20, 20
    xi = np.linspace(0, nx, std_num_x)
    yi = np.linspace(0, ny, std_num_y)
    xi, yi = np.meshgrid(xi, yi)
    # Resample the values onto the 20x20 grid
    coordinates = np.vstack([yi.flatten(), xi.flatten()])
    zi = map_coordinates(paw, coordinates)
    zi = zi.reshape(std_num_y, std_num_x)

    # Rescale the pressure values
    zi -= zi.min()
    zi /= zi.max()
    zi -= zi.mean() #<- Helps distinguish front from hind paws...
    return zi


def find_max_shape(data, data_slices):
    mx, my = 0, 0
    for dat_slice in data_slices:
        ty, tx, tz = np.shape(data[dat_slice])
        if ty > my:
            my = ty
        if tx > mx:
            mx = tx
    return pad_with_zeros(data, data_slices, mx, my)


def pad_with_zeros(data, data_slices, mx, my):
    padded = {}
    for contact_number, dat_slice in enumerate(data_slices):
        contact_number += 1
        ny, nx, nt = np.shape(data[dat_slice])
        offset_y, offset_x = int((my - ny) / 2), int((mx - nx) / 2)
        temp_array = np.zeros((my, mx))
        for y in range(ny):
            for x in range(nx):
                temp_array[y + offset_y, x + offset_x] = data[dat_slice].max(axis=2)[y, x]
        padded[contact_number] = temp_array
    return padded


def average_contacts(contacts):
    num_contacts = len(contacts)
    empty_array = np.zeros((50, 100, num_contacts)) # This should fit AN.THING
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        empty_array[0:nx, 0:ny, index] = contact # dump the array in the empty one
    average_array = np.mean(empty_array, axis=2)
    max_x, max_y = np.max(np.nonzero(average_array)[0]), np.max(np.nonzero(average_array)[1])
    average_array = average_array[0:max_x + 1, 0:max_y + 1]
    return average_array


def calculate_distance(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))


def fix_orientation(data):
    from scipy.ndimage.measurements import center_of_mass
    # Find the first and last frame with nonzero data (from z)
    x, y, z = np.nonzero(data)
    # For some reason I was loading the file in such a way that it wasn't sorted
    z = sorted(z)
    start, end = z[0], z[-1]
    # Get the COP for those two frames
    start_x, start_y = center_of_mass(data[:, :, start])
    end_x, end_y = center_of_mass(data[:, :, end])
    # We've calculated the start and end point of the measurement (if at all)
    x_distance = end_x - start_x
    # If this distance is negative, the dog walked right to left
    #print .The distance between the start and end is: {}".format(x_distance)
    if x_distance < 0:
        # So we flip the data around
        data = np.rot90(np.rot90(data))
    return data

def load_zebris(filename):
    """
    Input: raw text file, consisting of lines of strings
    Output: stacked numpy array (width x height x number of frames)

    This very crudely goes through the file, and if the line starts with an F splits it
    Then if the first word is Frame, it flips a boolean "frame_number" 
    and parses every line until we hit the closing "}".
    """
    with open(filename, "r") as infile:
        frame_number = None
        data_slices = []
        for line in infile:
            # This should prevent it from splitting every line
            if frame_number:
                if line[0] == 'y':
                    line = line.split()
                    data.append(line[1:])
                    # End of the frame
                if line[0] == '}':
                    data_slices.append(np.array(data, dtype=np.float32).T)
                    frame_number = None

            if line[0] == 'F':
                line = line.split()
                if line[0] == "Frame" and line[-1] == "{":
                    frame_number = line[1]
                    data = []
        results = np.dstack(data_slices)
        width, height, length = results.shape
        return results if width > height else results.swapaxes(0, 1)

# This functions is modified from:
# http://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
def load_rsscan(filename, padding=False):
    """Reads all data in the datafile. Returns an array of times for each
    slice, and a 3D array of pressure data with shape (nx, ny, nz)."""
    # Open the file
    with open(filename, "r") as infile:
        data_slices = []
        data = []
        for line in infile:
            split_line = line.strip().split()
            line_length = len(split_line)
            if line_length == 0:
                if len(data) != 0:
                    if padding:
                        empty_line = data[0]
                        data = [empty_line] + data + [empty_line]
                    array_data = np.array(data, dtype=np.float32)
                    data_slices.append(array_data)
            elif line_length == 4: # header
                data = []
            else:
                if padding:
                    split_line = ['0.0'] + split_line + ['0.0']
                data.append(split_line)

        result = np.dstack(data_slices)
        return result

def load(filename, padding=False, brand=configuration.brand):
    if brand == "rsscan":
        return load_rsscan(filename, padding)
    if brand == "zebris":
        # TODO add padding to the Zebris files
        return load_zebris(filename)

def convert_contour_to_slice(data, contact):
    # Get the bounding box for the entire contact
    center, min_x1, max_x1, min_y1, max_y1 = update_bounding_box(contact)
    frames = sorted(contact.keys())
    min_z, max_z = frames[0], frames[-1]
    # Create an empty array that should fit the entire contact
    newData = np.zeros_like(data)
    for frame, contours in list(contact.items()):
        # Pass a single frame dictionary as if it were a contact to get its bounding box
        center, min_x, max_x, min_y, max_y = update_bounding_box({frame: contours})
        # We need to slice around the contacts a little wider, I wonder what problems this might cause
        min_x, max_x, min_y, max_y = int(min_x), int(max_x) + 2, int(min_y), int(max_y) + 2
        newData[min_x:max_x, min_y:max_y, frame] = data[min_x:max_x, min_y:max_y, frame]
    return newData[min_x1 - 1:max_x1 + 2, min_y1 - 1:max_y1 + 2, min_z:max_z + 1]


def contour_to_polygon(contour, degree, offset_x=0, offset_y=0):
    # Loop through the contour, create a polygon out of it
    polygon = []
    coordinates = [[0][0]]  # Dummy coordinate
    for coordinates in contour:
        # Convert the points from the contour to QPointFs and add them to the list
        # The offset is used when you only display a slice, so you basically move the origin
        polygon.append(QPointF((coordinates[0][0] - offset_x) * degree, (coordinates[0][1] - offset_y) * degree))
        # If the contour has only a single point, add another point, that's right beside it
    if len(contour) == 1:
        polygon.append(QPointF((coordinates[0][0] + 1 - offset_x) * degree,
                               (coordinates[0][1] + 1 - offset_y) * degree)) # Pray this doesn't go out of bounds!
    return QPolygonF(polygon)


def contour_to_lines(contour):
    x = []
    y = []
    for point in contour:
        x.append(point[0][0])
        y.append(point[0][1])
    return x, y


def normalize(array, n_max):
    """
    This rescales all the values to be between 0-255
    """
    # If we have a non-zero offset, subtract the minimum
    if n_max == 0:
        return array

    scale = 255. / n_max
    array *= scale

    return array


def interpolate_frame(data, degree):
    """
    interpolate_frame interpolates one frame for a given degree. Don't insert a 3D array!
    """
    from scipy.ndimage import map_coordinates

    ny, nx = np.shape(data)
    std_num_x = nx * degree
    std_num_y = ny * degree
    # Based on a scientific guess
    # Make a 20x20 grid to resample the paw pressure values onto
    #std_num_x, std_num_y = 20, 20
    xi = np.linspace(0, nx, std_num_x)
    yi = np.linspace(0, ny, std_num_y)
    xi, yi = np.meshgrid(xi, yi)
    # Resample the values onto the 20x20 grid
    coordinates = np.vstack([yi.flatten(), xi.flatten()])
    zi = map_coordinates(data, coordinates)
    zi = zi.reshape(std_num_y, std_num_x)
    return zi


def average_contacts(contacts):
    num_contacts = len(contacts)
    empty_array = np.zeros((50, 100, num_contacts)) # This seems rather wasteful with space
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        empty_array[0:nx, 0:ny, index] = contact # dump the array in the empty one
    average_array = np.mean(empty_array, axis=2)
    max_x, max_y = np.max(np.nonzero(average_array)[0]), np.max(np.nonzero(average_array)[1])
    average_array = average_array[0:max_x + 1, 0:max_y + 1]
    return average_array


def calculate_cop(data):
    cop_x, cop_y = [], []
    y, x, z = np.shape(data)
    x_coordinate, y_coordinate = np.arange(1, x + 1), np.arange(1, y + 1)
    temp_x, temp_y = np.zeros((y, z)), np.zeros((x, z))
    for frame in range(z):
        if np.sum(data[:, :, frame]) != 0.0: # Else divide by zero
            for col in range(y):
                temp_x[col, frame] = np.sum(data[col, :, frame] * x_coordinate)
            for row in range(x):
                temp_y[row, frame] = np.sum(data[:, row, frame] * y_coordinate)
            if np.sum(temp_x[:, frame]) != 0.0 and np.sum(temp_y[:, frame]) != 0.0:
                cop_x.append(np.round(np.sum(temp_x[:, frame]) / np.sum(data[:, :, frame]), 2))
                cop_y.append(np.round(np.sum(temp_y[:, frame]) / np.sum(data[:, :, frame]), 2))
    return cop_x, cop_y


def scipy_cop(data):
    from scipy.ndimage.measurements import center_of_mass

    cop_x, cop_y = [], []
    height, width, length = data.shape
    for frame in range(length):
        y, x = center_of_mass(data[:, :, frame])
        cop_x.append(x + 1)
        cop_y.append(y + 1)
    return cop_x, cop_y


def get_QPixmap(data, degree, n_max, color_table):
    """
    This function expects a single frame, it will interpolate/resize it with a given degree and
    return a pixmap
    """
    from cv2 import resize, INTER_LINEAR
    # Need the sizes before reshaping
    width, height = data.shape
    # This can be used to interpolate, but it doesn't seem to work entirely correct yet...
    data = resize(data, (height * degree, width * degree), interpolation=INTER_LINEAR)
    # Normalize the data
    data = normalize(data, n_max)
    # Convert it from numpy to qimage
    qimage = array_to_qimage(data, color_table)
    # Convert the image to a pixmap
    pixmap = QPixmap.fromImage(qimage)
    # Scale up the image so its better visible
    #self.pixmap = self.pixmap.scaled(self.degree * self.height, self.degree * self.width,
    #                                 Qt.KeepAspectRatio, Qt.Fas.Transformation) #Qt.Smoot.Transformation
    return pixmap


def array_to_qimage(array, color_table):
    """Convert the 2D numpy array  into a 8-bit QImage with a gray
    colormap.  The first dimension represents the vertical image axis."""
    array = np.require(array, np.uint8, 'C')
    width, height = array.shape
    result = QImage(array.data, height, width, QImage.Format_Indexed8)
    result.ndarray = array
    # Use the default one from this library
    result.setColorTable(color_table)
    # Convert it to RGB32
    result = result.convertToFormat(QImage.Format_RGB32)
    return result


def interpolate_rgb(start_color, start_value, end_color, end_value, actual_value):
    delta_value = end_value - start_value
    if delta_value == 0.0:
        return start_color

    multiplier = (actual_value - start_value) / delta_value

    start_red = (start_color >> 16) & 0xff
    end_red = (end_color >> 16) & 0xff
    delta_red = end_red - start_red
    red = start_red + (delta_red * multiplier)

    if delta_red > 0:
        if red < start_red:
            red = start_red
        elif red > end_red:
            red = end_red
    else:
        if red > start_red:
            red = start_red
        elif red < end_red:
            red = end_red

    start_green = (start_color >> 8) & 0xff
    end_green = (end_color >> 8) & 0xff
    delta_green = end_green - start_green
    green = start_green + (delta_green * multiplier)

    if delta_green > 0:
        if green < start_green:
            green = start_green
        elif green > end_green:
            green = end_green
    else:
        if green > start_green:
            green = start_green
        elif green < end_green:
            green = end_green

    start_blue = start_color & 0xff
    end_blue = end_color & 0xff
    delta_blue = end_blue - start_blue
    blue = start_blue + (delta_blue * multiplier)

    if delta_blue > 0:
        if blue < start_blue:
            blue = start_blue
        elif blue > end_blue:
            blue = end_blue
    else:
        if blue > start_blue:
            blue = start_blue
        elif blue < end_blue:
            blue = end_blue

    return qRgb(red, green, blue)


class ImageColorTable():
    def __init__(self):
        self.black = QColor(0, 0, 0).rgb()
        self.lightblue = QColor(0, 0, 255).rgb()
        self.blue = QColor(0, 0, 255).rgb()
        self.cyan = QColor(0, 255, 255).rgb()
        self.green = QColor(0, 255, 0).rgb()
        self.yellow = QColor(255, 255, 0).rgb()
        self.orange = QColor(255, 128, 0).rgb()
        self.red = QColor(255, 0, 0).rgb()
        self.white = QColor(255, 255, 255).rgb()

        self.black_threshold = 0.01
        self.lightblue_threshold = 1.00
        self.blue_threshold = 4.83
        self.cyan_threshold = 10.74
        self.green_threshold = 21.47
        self.yellow_threshold = 93.94
        self.orange_threshold = 174.0
        self.red_threshold = 256.0

    def create_color_table(self):
        color_table = [self.black for _ in range(255)]
        for val in range(255):
            if val < self.black_threshold:
                color_table[val] = interpolate_rgb(self.black, self.black_threshold,
                                                   self.blue, self.blue_threshold, val)
            else:
                if val <= self.yellow_threshold:
                    if val <= self.cyan_threshold:
                        if val <= self.blue_threshold:
                            color_table[val] = interpolate_rgb(self.blue, self.black_threshold,
                                                               self.lightblue, self.blue_threshold, val)
                        else:
                            color_table[val] = interpolate_rgb(self.lightblue, self.blue_threshold,
                                                               self.cyan, self.cyan_threshold, val)
                    else:
                        if val <= self.green_threshold:
                            color_table[val] = interpolate_rgb(self.cyan, self.cyan_threshold,
                                                               self.green, self.green_threshold, val)
                        else:
                            color_table[val] = interpolate_rgb(self.green, self.green_threshold,
                                                               self.yellow, self.yellow_threshold, val)
                else:
                    if val <= self.orange_threshold:
                        color_table[val] = interpolate_rgb(self.yellow, self.yellow_threshold,
                                                           self.orange, self.orange_threshold, val)
                    elif val <= self.red_threshold:
                        color_table[val] = interpolate_rgb(self.orange, self.orange_threshold,
                                                           self.red, self.red_threshold, val)
        return color_table


def touches_edges(data, paw, padding=False):
    ny, nx, nt = data.shape
    if not padding:
        x_touch = (paw.total_min_x == 0) or (paw.total_max_x == ny)
        y_touch = (paw.total_min_y == 0) or (paw.total_max_y == nx)
        z_touch = (paw.frames[-1] == nt)
    else:
        x_touch = (paw.total_min_x <= 1) or (paw.total_max_x >= ny - 1)
        y_touch = (paw.total_min_y <= 1) or (paw.total_max_y >= nx - 1)
        z_touch = (paw.frames[-1] >= nt - 1)
    return x_touch or y_touch or z_touch


def incomplete_step(data_slice):
    pressure_over_time = np.sum(np.sum(data_slice, axis=0), axis=0)
    max_pressure = np.max(pressure_over_time)
    incomplete = False
    if pressure_over_time[0] > (0.1 * max_pressure) or pressure_over_time[-1] > (0.1 * max_pressure):
        incomplete = True
    return incomplete


def agglomerative_clustering(data, num_clusters):
    from collections import defaultdict
    import heapq

    distances = defaultdict(dict)
    heap = []

    clusters = {}
    leaders = {}

    for index1, trial1 in enumerate(data):
        clusters[index1] = {index1}
        leaders[index1] = index1
        for index2, trial2 in enumerate(data):
            if index1 != index2:
                dist = np.sum(np.sqrt((trial1 - trial2) ** 2))
                #dist = np.sum(trial1 - trial2)
                distances[index1][index2] = dist
                heapq.heappush(heap, (dist, (index1, index2)))

    explored = set()
    # Keep going as long as there are clusters left
    while heap and len(clusters) > num_clusters:
        dist, (index1, index2) = heapq.heappop(heap)
        leader1 = leaders[index1]
        leader2 = leaders[index2]

        if leader1 != leader2 and index1 not in explored:
            explored.add(index1)
            #explored.add(index2)
            for node in clusters[leader2]:
                clusters[leader1].add(node)
                leaders[node] = leader1
                if node in clusters:
                    del clusters[node]

    labels = [0 for _ in range(len(leaders))]
    keys = list(clusters.keys())
    for leader in clusters:
        for node in clusters[leader]:
            labels[node] = keys.index(leader)

    return labels


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def piecewise_aggregate_approximation(data, step_size=3):
    return [np.mean(chunk) for chunk in chunks(data, step_size)]


def map_to_string(piecewise_aggregate_approximation, alphabet_size):
    """
    I'm not sure whether using len here is appropriate
    Shouldn't I be using shape and testing if we even have the appropriate format?
    """
    result = np.zeros((len(piecewise_aggregate_approximation)))

    mapping = {
        2: [float("-inf"), 0],
        3: [float("-inf"), -0.43, 0.43],
        4: [float("-inf"), -0.67, 0, 0.67],
        5: [float("-inf"), -0.84, -0.25, 0.25, 0.84],
        6: [float("-inf"), -0.97, -0.43, 0, 0.43, 0.97],
        7: [float("-inf"), -1.07, -0.57, -0.18, 0.18, 0.57, 1.07],
        8: [float("-inf"), -1.15, -0.67, -0.32, 0, 0.32, 0.67, 1.15],
        9: [float("-inf"), -1.22, -0.76, -0.43, -0.14, 0.14, 0.43, 0.76, 1.22],
        10: [float("-inf"), -1.28, -0.84, -0.52, -0.25, 0., 0.25, 0.52, 0.84, 1.28],
        11: [float("-inf"), -1.34, -0.91, -0.6, -0.35, -0.11, 0.11, 0.35, 0.6, 0.91, 1.34],
        12: [float("-inf"), -1.38, -0.97, -0.67, -0.43, -0.21, 0, 0.21, 0.43, 0.67, 0.97, 1.38],
        13: [float("-inf"), -1.43, -1.02, -0.74, -0.5, -0.29, -0.1, 0.1, 0.29, 0.5, 0.74, 1.02, 1.43],
        14: [float("-inf"), -1.47, -1.07, -0.79, -0.57, -0.37, -0.18, 0, 0.18, 0.37, 0.57, 0.79, 1.07, 1.47],
        15: [float("-inf"), -1.5, -1.11, -0.84, -0.62, -0.43, -0.25, -0.08, 0.08, 0.25, 0.43, 0.62, 0.84, 1.11, 1.5],
        16: [float("-inf"), -1.53, -1.15, -0.89, -0.67, -0.49, -0.32, -0.16, 0, 0.16, 0.32, 0.49, 0.67, 0.89, 1.15,
             1.53],
        17: [float("-inf"), -1.56, -1.19, -0.93, -0.72, -0.54, -0.38, -0.22, -0.07, 0.07, 0.22, 0.38, 0.54, 0.72, 0.93,
             1.19, 1.56],
        18: [float("-inf"), -1.59, -1.22, -0.97, -0.76, -0.59, -0.43, -0.28, -0.14, 0, 0.14, 0.28, 0.43, 0.59, 0.76,
             0.97,
             1.22, 1.59],
        19: [float("-inf"), -1.62, -1.25, -1, -0.8, -0.63, -0.48, -0.34, -0.2 - 0.07, 0.07, 0.2, 0.34, 0.48, 0.63, 0.8,
             1,
             1.25, 1.62],
        20: [float("-inf"), -1.64, -1.28, -1.04, -0.84, -0.67, -0.52, -0.39, -0.25, -0.13, 0, 0.13, 0.25, 0.39, 0.52,
             0.67,
             0.84, 1.04, 1.28, 1.64],
    }
    # Get the right cut-off point from the mapping
    cut_points = mapping[alphabet_size]
    for i in range(len(piecewise_aggregate_approximation)):
        result[i] = np.sum((cut_points <= piecewise_aggregate_approximation[i]))
    return result


def timeseries2symbol(data, N, n, alphabet_size):
    """
    N = data_len or sliding window
    n = nseg
    When calculating the ratio N / n, make sure one of them is a float!
    Use as: current_string = timeseries2symbol(data, data_len, nseg, alphabet_size)
    """
    from math import floor

    if alphabet_size > 20:
        print("Alphabet is too large!")

    win_size = int(floor(N / n))
    piecewise_aggregate_approximation = []  # Dummy variable

    # If N == data_len, then this will only be done once
    # So then we don't use a sliding window
    for i in range(len(data) - (N - 1)):
    # Slice the data
        sub_section = data[i:i + N]
        # Z normalize it
        # Turned off for now, since its already applied, but then to the entire dataset
        sub_section = (sub_section - np.mean(sub_section)) / np.std(sub_section)

        # If the data is as long as the number of segments, we don't have to piecewise_aggregate_approximation
        if N == n:
            piecewise_aggregate_approximation = sub_section
        else:
            # Check if we have the right number of segments
            # If this check doesn't work anymore, its because of lacking parentheses
            if N / float(n) - floor(N / n): # If this is not zero, the ratio is off
                # Tile the sub_sections
                temp = np.tile(data[:, None], n)
                # Unroll the subsections from N x n to 1 x (N*n)
                expanded_sub_section = np.reshape(temp, (1, N * n))
                piecewise_aggregate_approximation = np.mean(np.reshape(expanded_sub_section, (n, N)), axis=1)
            else:
                # This last part can probably be rewritten, so I only have to piecewise_aggregate_approximation once.
                # But we'll wait until we know it actually works!
                piecewise_aggregate_approximation = np.mean(np.reshape(sub_section, (n, win_size)), axis=1)

    current_string = map_to_string(piecewise_aggregate_approximation, alphabet_size)
    # Here follow so steps related to pointers, but I have no idea what for
    # They also delete the first item from symbolic_data, which is being returned
    # But I think that's only important if you really use the sliding window in some way
    return current_string


def saxify(data, n=10, alphabet_size=4):
    """
    data is expected to be a 1D time serie
    n = number of segments
    alphabet_size has to be 2 < size < 20, defines how the number of intervals in Y
    Assumes numpy is imported as np
    """
    from math import floor

    N = len(data)
    win_size = int(floor(N / n))
    # Do I want to Z-normalize?
    data = (data - np.mean(data)) / np.std(data)

    # Check if we have the right number of segments
    if N / float(n) - floor(N / n):  # If this is not zero, the ratio is off
        # Tile the sub_sections
        temp = np.tile(data[:, None], n)
        # Unroll the subsections from N x n to 1 x (N*n)
        expanded_sub_section = np.reshape(temp, (1, N * n))
        piecewise_aggregate_approximation = np.mean(np.reshape(expanded_sub_section, (n, N)), axis=1)
    else:
        piecewise_aggregate_approximation = np.mean(np.reshape(data, (n, win_size)), axis=1)

    current_string = map_to_string(piecewise_aggregate_approximation, alphabet_size)
    return current_string


def build_dist_table(alphabet_size):
    """
    Given the alphabet size, build the distance table for the (squared) minimum distances
    between different symbols
    """
    mapping = {
        2: [-0.43, 0.43],
        3: [-0.67, 0, 0.67],
        4: [-0.84, -0.25, 0.25, 0.84],
        5: [-0.97, -0.43, 0, 0.43, 0.97],
        6: [-1.07, -0.57, -0.18, 0.18, 0.57, 1.07],
        7: [-1.15, -0.67, -0.32, 0, 0.32, 0.67, 1.15],
        8: [-1.22, -0.76, -0.43, -0.14, 0.14, 0.43, 0.76, 1.22],
        9: [-1.28, -0.84, -0.52, -0.25, 0., 0.25, 0.52, 0.84, 1.28],
        10: [-1.34, -0.91, -0.6, -0.35, -0.11, 0.11, 0.35, 0.6, 0.91, 1.34],
        11: [-1.38, -0.97, -0.67, -0.43, -0.21, 0, 0.21, 0.43, 0.67, 0.97, 1.38],
        12: [-1.43, -1.02, -0.74, -0.5, -0.29, -0.1, 0.1, 0.29, 0.5, 0.74, 1.02, 1.43],
        13: [-1.47, -1.07, -0.79, -0.57, -0.37, -0.18, 0, 0.18, 0.37, 0.57, 0.79, 1.07, 1.47],
        14: [-1.5, -1.11, -0.84, -0.62, -0.43, -0.25, -0.08, 0.08, 0.25, 0.43, 0.62, 0.84, 1.11, 1.5],
        15: [-1.53, -1.15, -0.89, -0.67, -0.49, -0.32, -0.16, 0, 0.16, 0.32, 0.49, 0.67, 0.89, 1.15, 1.53],
        16: [-1.56, -1.19, -0.93, -0.72, -0.54, -0.38, -0.22, -0.07, 0.07, 0.22, 0.38, 0.54, 0.72, 0.93, 1.19, 1.56],
        17: [-1.59, -1.22, -0.97, -0.76, -0.59, -0.43, -0.28, -0.14, 0, 0.14, 0.28, 0.43, 0.59, 0.76, 0.97, 1.22, 1.59],
        18: [-1.62, -1.25, -1, -0.8, -0.63, -0.48, -0.34, -0.2 - 0.07, 0.07, 0.2, 0.34, 0.48, 0.63, 0.8, 1, 1.25, 1.62],
        19: [-1.64, -1.28, -1.04, -0.84, -0.67, -0.52, -0.39, -0.25, -0.13, 0, 0.13, 0.25, 0.39, 0.52, 0.67, 0.84, 1.04,
             1.28, 1.64],
    }
    cutlines = mapping[alphabet_size]
    dist_matrix = np.zeros((alphabet_size, alphabet_size))
    for i in range(alphabet_size):
        # the min_dist for adjacent symbols are 0, so we start with i+2
        for j in range(i, alphabet_size):
            # Get the squared difference
            dist_matrix[i, j] = (cutlines[i] - cutlines[j]) ** 2
            dist_matrix[j, i] = dist_matrix[i, j]
    return dist_matrix


def calc_distances(str1, str2, alphabet_size):
    dist_matrix = build_dist_table(alphabet_size)
    distances = np.zeros((len(str1), len(str2)))
    for idx1, i in enumerate(str1):
        for idx2, j in enumerate(str2):
            # Why on earth I have to use -1 is beyond me
            distances[idx1, idx2] = dist_matrix[i - 1, j - 1]
    return distances


def min_dist(str1, str2, alphabet_size, compression_ratio):
    """
    This function computes the minimum (lower-bounding) distance between two strings.  The strings
    should have equal length.
    Input:
        str1: first string
        str2: second string
        alphabet_size: alphabet_size used to construct the strings
        compression_ratio: original_data_len / symbolic_len
    Output:
        dist: lower-bounding distance
    """
    if len(str1) != len(str2):
        print("Error: strings must have equal length!")
        return

    # Wait does this check whether any of the chars
    # Matlab: if (any(str1 > alphabet_size) | any(str2 > alphabet_size))
    if any(str1 > alphabet_size) or any(str2 > alphabet_size):
        print("Error: some symbols in the string exceed the alphabet_size!")
        return

    distances = calc_distances(str1, str2, alphabet_size)
    dist = np.sqrt(compression_ratio * sum(np.diagonal(distances)))

    return dist


def distance_between_centers(center1, center2):
    x1, y1 = center1
    x2, y2 = center2
    dx = x1 - x2
    dy = y1 - y2
    return (dx * dx + dy * dy) ** 0.5


mapping = {
    2: [float("-inf"), 0],
    3: [float("-inf"), -0.43, 0.43],
    4: [float("-inf"), -0.67, 0, 0.67],
    5: [float("-inf"), -0.84, -0.25, 0.25, 0.84],
    6: [float("-inf"), -0.97, -0.43, 0, 0.43, 0.97],
    7: [float("-inf"), -1.07, -0.57, -0.18, 0.18, 0.57, 1.07],
    8: [float("-inf"), -1.15, -0.67, -0.32, 0, 0.32, 0.67, 1.15],
    9: [float("-inf"), -1.22, -0.76, -0.43, -0.14, 0.14, 0.43, 0.76, 1.22],
    10: [float("-inf"), -1.28, -0.84, -0.52, -0.25, 0., 0.25, 0.52, 0.84, 1.28],
    11: [float("-inf"), -1.34, -0.91, -0.6, -0.35, -0.11, 0.11, 0.35, 0.6, 0.91, 1.34],
    12: [float("-inf"), -1.38, -0.97, -0.67, -0.43, -0.21, 0, 0.21, 0.43, 0.67, 0.97, 1.38],
    13: [float("-inf"), -1.43, -1.02, -0.74, -0.5, -0.29, -0.1, 0.1, 0.29, 0.5, 0.74, 1.02, 1.43],
    14: [float("-inf"), -1.47, -1.07, -0.79, -0.57, -0.37, -0.18, 0, 0.18, 0.37, 0.57, 0.79, 1.07, 1.47],
    15: [float("-inf"), -1.5, -1.11, -0.84, -0.62, -0.43, -0.25, -0.08, 0.08, 0.25, 0.43, 0.62, 0.84, 1.11, 1.5],
    16: [float("-inf"), -1.53, -1.15, -0.89, -0.67, -0.49, -0.32, -0.16, 0, 0.16, 0.32, 0.49, 0.67, 0.89, 1.15, 1.53],
    17: [float("-inf"), -1.56, -1.19, -0.93, -0.72, -0.54, -0.38, -0.22, -0.07, 0.07, 0.22, 0.38, 0.54, 0.72, 0.93,
         1.19, 1.56],
    18: [float("-inf"), -1.59, -1.22, -0.97, -0.76, -0.59, -0.43, -0.28, -0.14, 0, 0.14, 0.28, 0.43, 0.59, 0.76, 0.97,
         1.22, 1.59],
    19: [float("-inf"), -1.62, -1.25, -1, -0.8, -0.63, -0.48, -0.34, -0.2 - 0.07, 0.07, 0.2, 0.34, 0.48, 0.63, 0.8, 1,
         1.25, 1.62],
    20: [float("-inf"), -1.64, -1.28, -1.04, -0.84, -0.67, -0.52, -0.39, -0.25, -0.13, 0, 0.13, 0.25, 0.39, 0.52, 0.67,
         0.84, 1.04, 1.28, 1.64],
}


