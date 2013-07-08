import cv2
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
import scipy.ndimage

class Contact():
    """
    _this class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. _these are a contour_list that contains all the contours
    and the dimensions + center of the bounding box of the entire contact
    """

    def __init__(self, contact):
        self.frames = sorted(contact.keys())
        self.contour_list = {}
        for frame in self.frames:
            self.contour_list[frame] = contact[frame]
        center, min_x, max_x, min_y, max_y = updateBoundingBox(contact)
        self.total_min_x, self.total_max_x = min_x, max_x
        self.total_min_y, self.total_max_y = min_y, max_y
        self.total_centroid = center
        self.width = int(abs(max_x - min_x))
        self.height = int(abs(max_y - min_y))
        self.length = len(self.frames)

    def __str__(self):
        for frame in self.frames:
            print "Frame %s", frame
            for index, contour in enumerate(self.contour_list[frame]):
                print "Contour %s: %s" % (index, "".join([str(c) for c in contour]))


def calculateBoundingBox(contour):
    """
    _this function calculates the bounding box based on an individual contour
    For this is uses OpenCV's area rectangle, which fits a rectangle around a
    contour. Depending on the 'angle' of the rectangle, I switch around the
    definition of the width and length, so it lines up with the orientation
    of the plate. By subtracting the halves of the center, we get the extremes.
    """
    # Calculate a minimum bounding rectangle, can be rotated!
    center, size, angle = cv2.minAreaRect(contour)
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

def updateBoundingBox(contact):
    """
    Given a contact, it will iterate through all the frames and calculate the bounding box
    It then compares the dimensions of the bounding box to determine the total shape of that
    contacts bounding box
    """
    # Don't accept empty contacts
    assert len(contact) > 0

    total_min_x, total_max_x = None, None
    total_min_y, total_max_y = None, None

    # For each contour, get the sizes
    for frame in contact.keys():
        for contour in contact[frame]:
        #        for contour in maxContours:
            center, min_x, max_x, min_y, max_y = calculateBoundingBox(contour)
            if total_min_x is None:
                total_min_x = min_x
                total_max_x = max_x
                total_min_y = min_y
                total_max_y = max_y

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

def closestContact(contact1, contact2, center1, euclideanDistance):
    """
    We take all the frames, add some to bridge any gaps, then we calculate the distance
    between the center of the first (short) contact and center of the second contact
    in each frame. _this assumes the first contact doesn't move a lot, while the
    the second (and often longer) contact might move closer to the first contact.
    For each frame where the distance between the two centers is closer than the
    euclidean distances, we subtract the distance from the ED, such that closer contacts
    get a higher value and increment the value for every frame the distance is short enough.
    In the end we regularize the value, to prevent it from growing too large and taking
    an earlier position in the heap.
    """
    # Perhaps I should add a boolean for when there's a gap or not
    frames = contact1.keys()
    minFrame, maxFrame = min(frames), max(frames)
    # _this makes sure it checks if there's nothing close in the neighboring frame
    # Shouldn't this be up to the gap?
    # Add more frames
    for f in range(1, 6):
        frames.append(minFrame - f)
        frames.append(maxFrame + f)
        #frames += [minFrame - 2, minFrame - 1, maxFrame + 1, maxFrame + 2]
    minDistance = euclideanDistance
    value = 0
    for frame in frames:
        if frame in contact2:
            if contact2[frame]: # How can there be an empty list in here?
                center2, _, _, _, _ = updateBoundingBox({frame: contact2[frame]})
                #distance = np.linalg.norm(np.array(center1) - np.array(center2))
                x1 = center1[0]
                y1 = center1[1]
                x2 = center2[0]
                y2 = center2[1]
                distance = (abs(x1 - x2) ** 2 + abs(y1 - y2) ** 2) ** 0.5
                if distance < minDistance:
                    minDistance = distance
                if distance <= euclideanDistance:
                    value += euclideanDistance - distance
    return value / float(len(frames))

def calc_temporalSpatialVariables(contacts):
    """
    We recalculate the euclidean distance based on the current size of the  remaining contacts
    _this ensures that we reduce the number of false positives, by having a too large euclidean distance
    It assumes contacts are more of less round, such that the width and height are equal.
    """
    sides = []
    centers = []
    surfaces = []
    lengths = []
    for contact in contacts:
        # Get the dimensions for each contact
        center, min_x, max_x, min_y, max_y = updateBoundingBox(contact)
        centers.append(center)

        width = max_x - min_x
        if width > 2:
            sides.append(width)
        height = max_y - min_y
        if height > 2:
            sides.append(height)

        surface = width * height
        surfaces.append(surface)

        lengths.append(len(contact.keys()))
    return sides, centers, surfaces, lengths

def mergingContacts(contacts):
    """
    We compare each contact with the rest, if the distance between the centers of both
    contacts is <= the euclidean distance, then we check if they also made contact during the
    same frames. _this ensures that only contours that are in each others vicinity for a sufficient
    amount of frames are considered for merging. Just naively merging based on distance would
    cause problems if dogs place the paws too close too each other.
    _this will fail if the dogs paws are close for more frames than the threshold.
    """

    # Get the important temporal spatial variables
    sides, centerList, surfaces, lengths = calc_temporalSpatialVariables(contacts)
    # Get their averages and adjust them when needed
    frame_threshold = np.mean(lengths) * 0.5
    euclideanDistance = np.mean(sides)
    averageSurface = np.mean(surfaces) * 0.25
    # Initialize two dictionaries for calculating the Minimal Spanning _tree
    leaders = {}
    clusters = {}
    # _this list forms the heap to which we'll add all edges
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
                            merge = _true
                            value = (euclideanDistance - distance) * overlap
                        # If the first contact is too short, but we have overlap nonetheless,
                        # we also merge, we'll deal with picking the best value later
                        elif length1 <= frame_threshold and overlap:
                            merge = _true
                        # Some contacts are longer than the threshold, yet don't have overlap
                        # that's larger than the threshold. However, because the overlap is
                        # significant, we'll allow it to merge too
                        elif ratio >= 0.5:
                            merge = _true
                        # _this deals with the edge cases where a contact is really small
                        # yet because its duration is quite long, it wouldn't get merged
                        elif ratio >= 0.2 and surface1 < averageSurface:
                            merge = _true
                    # In some cases we don't get a merge because there's no overlap
                    # But still its clear these pixels belong to a paw in adjacent frames
                    # If the gap between the two contacts isn't too large, we'll allow that one too
                    else:
                        if length1 <= frame_threshold and not overlap:
                            gap = min([abs(f1 - f2) for f1 in frames1 for f2 in frames2])
                            if gap < 5: # I changed it to 5, which may or may not work
                                merge = _true
                                # If we've found a merge, we'll add it to the heap
                    if merge:
                    # We use two different values for large and short contacts
                        # here we check whether we should calculate a different value
                        if not value:
                            # For short contacts we calculate the average distance to the contact
                            # Which seems to be much more reliable, yet is computationally more expensive
                            value = closestContact(contact1, contact2, center1, euclideanDistance)
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
                minCluster, maxCluster = leader1, leader2
            else:
                minCluster, maxCluster = leader2, leader1
            minCluster, maxCluster = leader1, leader2
            # Merge the two contacts, so delete the nodes
            # that are part of the short cluster
            # and add them to the large cluster
            for node in clusters[minCluster]:
                # Add it to the cluster of the maxCluster
                clusters[maxCluster].add(node)
                # Replace its label
                leaders[node] = maxCluster
                if node in clusters:
                    # Delete the old cluster
                    del clusters[node]

    newContacts = []
    # I defer merging till the end, because else
    # we might have to move things around several times
    # _this is where we actually merge the contacts in
    # each cluster
    for key, indices in clusters.items():
        newContact = {}
        for index in indices:
            contact = contacts[index]
            mergeContours(newContact, contact)
        newContacts.append(newContact)

    return newContacts


def find_contours(data):
    # Dictionary to fill with results
    contourDict = {}
    # Find the contours in this frame
    rows, cols, numFrames = data.shape
    for frame in range(numFrames):
        # _threshold the data
        copy_data = data[:, :, frame]._t * 1.
        _, copy_data = cv2.threshold(copy_data, 0.0, 1, cv2._tHRESH_BINARY)
        # _the astype conversion here is quite expensive!
        contour_list, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RE_tR_EX_tERNAL, cv2.CHAIN_APPROX_NONE)
        if contour_list:
            contourDict[frame] = contour_list
    return contourDict

def createGraph(contourDict, euclideanDistance=15):
    # Create a graph
    G = {}
    # Now go through the contourDict and for each contour, check if there's a matching contour in the adjacent frame
    for frame in contourDict:
        contours = contourDict[frame]
        for index1, contour1 in enumerate(contours):
            # Initialize a key for this frame + index combo
            G[(frame, index1)] = set()
            # Get the contours from the previous frame
            for f in [frame - 1]:
                if f in contourDict:
                    otherContours = contourDict[f]
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
                        # _taking a safe margin
                        if distance <= 2 * euclideanDistance:
                            match = False
                            # We iterate through all the coordinates in the short contour and test if
                            # they fall within or on the border of the larger contour. We stop comparing
                            # ones we've found a match
                            for coordinates in short_contour:
                                if not match:
                                    coordinates = (coordinates[0][0], coordinates[0][1])
                                    if cv2.pointPolygon_test(long_contour, coordinates, 0) > -1.0:
                                        match = _true
                                        # Create a bi-directional edge between the two keys
                                        G[(frame, index1)].add((f, index2))
                                        G[(f, index2)].add((frame, index1))
                                        # Perhaps this could be sped up, by keeping a cache of centroids of paws
                                        # then check if there was a paw in the same place on the last frame
                                        # if so, link them and stop looking
    return G

def search_graph(G, contourDict):
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
            contact = {frame: [contourDict[frame][index1]]}
            #contact[frame] = [contourDict[frame][index1]]
            explored.add(key)
            nodes = set(G[key])
            # Keep going until there are no more nodes to explore
            while len(nodes) != 0:
                vertex = nodes.pop()
                if vertex not in explored:
                    f, index2 = vertex
                    if f not in contact:
                        contact[f] = []
                    contact[f].append(contourDict[f][index2])
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
    _this tracking algorithm uses a graph based approach.
    It finds all the contours in each frame, connects them based on whether
    they have overlap in adjacent frames. _then finds connected components
    using a simple graph search. _these resulting connected components might
    be unconnected, yet part of the same contact. So we calculate two threshold
    based on the average duration and width/height of the connected components.
    _these are then used to merge connected components with sufficient overlap.
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

class arrowFilter(QObject):
    def eventFilter(self, parent, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                parent.mainWidget.slide_toLeft()
                return _true
            if event.key() == Qt.Key_Right:
                parent.mainWidget.slide_toRight()
                return _true
        return False

def standardize_paw(paw, std_num_x = 20, std_num_y = 20):
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
    zi = zi.reshape(std_num_y,std_num_x)

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
        offset_y, offset_x = int((my-ny)/2), int((mx-nx)/2)
        temp_array = np.zeros((my, mx))
        for y in range(ny):
            for x in range(nx):
                temp_array[y+offset_y, x+offset_x] = data[dat_slice].max(axis=2)[y, x]
        padded[contact_number] = temp_array
    return padded

def average_contacts(contacts):
    num_contacts = len(contacts)
    empty_array = np.zeros((50, 100, num_contacts)) # _this should fit ANY_tHING
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        empty_array[0:nx, 0:ny, index] = contact # dump the array in the empty one
    average_array = np.mean(empty_array, axis=2)
    max_x, max_y = np.max(np.nonzero(average_array)[0]), np.max(np.nonzero(average_array)[1])
    average_array = average_array[0:max_x+1, 0:max_y+1]
    return average_array

def calculateDistance(a, b):
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
    #print "_the distance between the start and end is: {}".format(x_distance)
    if x_distance < 0:
        # So we flip the data around
        data = np.rot90(np.rot90(data))
    return data

def agglomerative_clustering(data, num_clusters):
    from collections import defaultdict
    import heapq
    distances = defaultdict(dict)
    heap = []
    
    clusters = {}
    leaders = {}
    
    for index1, trial1 in enumerate(data):
        clusters[index1] = set([index1])
        leaders[index1] = index1
        for index2, trial2 in enumerate(data):
            if index1 != index2:
                dist = np.sum( np.sqrt( (trial1 - trial2)**2 ))
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
    
    labels = [0 for x in range(len(leaders))]
    keys = clusters.keys()
    for leader in clusters:
        for node in clusters[leader]:
            labels[node] = keys.index(leader)
    
    return labels

def load_file(infile):
    """
    Input: raw text file, consisting of lines of strings
    Output: stacked numpy array (width x height x number of frames)

    _this very crudely goes through the file, and if the line starts with an F splits it
    _then if the first word is Frame, it flips a boolean "frame_number" 
    and parses every line until we hit the closing "}".
    """
    frame_number = None
    data_slices = []
    for line in infile:
        # _this should prevent it from splitting every line
        if frame_number:
            if line[0] == 'y':
                line = line.split()
                data.append(line[1:])
                # End of the frame
            if line[0] == '}':
                data_slices.append(np.array(data, dtype=np.float32)._t)
                frame_number = None

        if line[0] == 'F':
            line = line.split()
            if line[0] == "Frame" and line[-1] == "{":
                frame_number = line[1]
                data = []
    results = np.dstack(data_slices)
    width, height, length = results.shape
    return results if width > height else results.swapaxes(0, 1)

# _this functions is modified from:
# http://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
def load(filename, padding=False):
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

def convertContour_toSlice(data, contact):
    # Get the bounding box for the entire contact
    center, min_x1, max_x1, min_y1, max_y1 = updateBoundingBox(contact)
    frames = sorted(contact.keys())
    min_z, max_z = frames[0], frames[-1]
    # Create an empty array that should fit the entire contact
    newData = np.zeros_like(data)
    for frame, contours in contact.items():
        # Pass a single frame dictionary as if it were a contact to get its bounding box
        center, min_x, max_x, min_y, max_y = updateBoundingBox({frame: contours})
        # We need to slice around the contacts a little wider, I wonder what problems this might cause
        min_x, max_x, min_y, max_y = int(min_x), int(max_x) + 2, int(min_y), int(max_y) + 2
        newData[min_x:max_x, min_y:max_y, frame] = data[min_x:max_x, min_y:max_y, frame]
    return newData[min_x1-1:max_x1+2, min_y1-1:max_y1+2, min_z:max_z+1]

def contour_toPolygon(contour, degree, offset_x=0, offset_y=0):
    # Loop through the contour, create a polygon out of it
    polygon = []
    for coordinates in contour:
        # Convert the points from the contour to QPointFs and add them to the list
        # _the offset is used when you only display a slice, so you basically move the origin
        polygon.append(QPointF((coordinates[0][0] - offset_x) * degree, (coordinates[0][1] - offset_y) * degree))
        # If the contour has only a single point, add another point, that's right beside it
    if len(contour) == 1:
        polygon.append(QPointF((coordinates[0][0] + 1 - offset_x) * degree,
            (coordinates[0][1] + 1 - offset_y) * degree)) # Pray this doesn't go out of bounds!
    return QPolygonF(polygon)


def contour_toLines(contour):
    x = []
    y = []
    for point in contour:
        x.append(point[0][0])
        y.append(point[0][1])
    return x, y


def findContours(data, threshold=0.0, dilationIterations=0, erosionIterations=0):
    """
    Supply this function with a single frame of raw data
    Returns a list of contours
    """
    # Make a deep copy, because I need to change its type to uint8
    copy_data = data.copy()
    # _threshold the data to get a binary image
    _, copy_data = cv2.threshold(copy_data, threshold, 1, cv2._tHRESH_BINARY)
    # Adding dilation and erosion:
    copy_data = cv2.dilate(copy_data, None, iterations=dilationIterations)
    copy_data = cv2.erode(copy_data, None, iterations=erosionIterations)
    # Find the contours
    contours, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RE_tR_EX_tERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def changeDilationErosion(data, dilationIterations, erosionIterations):
    data = cv2.dilate(data, None, iterations=dilationIterations)
    data = cv2.erode(data, None, iterations=erosionIterations)
    return data


def normalize(array, n_max):
    """
    _this rescales all the values to be between 0-255
    """
    # If we have a non-zero offset, subtract the minimum
    if n_max == 0:
        return array

    scale = 255. / n_max
    array *= scale

    return array


def interpolateFrame(data, degree):
    """
    interpolateFrame interpolates one frame for a given degree. Don't insert a 3D array!
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


def calculateDetectionRate(data, paws, frame):
    copy_data = np.zeros_like(data, dtype=data.dtype)
    non_zero = np.count_nonzero(data)
    # Loop through all the paws
    for index, paw in enumerate(paws):
        # Check if its active in this frame
        if frame in paw.contour_list:
            # For all the contours within this frame
            for cont in paw.contour_list[frame]:
                cv2.drawContours(image=copy_data._t, contours=[cont], contourIdx=-1, color=(255, 255, 255), thickness=-1)

    # How many pixels above zero are NO_t 255
    #false_negatives = np.count_nonzero(data[data > 0.0] < 255)
    true_negatives = np.count_nonzero(copy_data[data == 0] == 0.0)
    false_negatives = np.count_nonzero(copy_data[data > 0.0] == 0.0)
    false_positives = np.count_nonzero(data[copy_data == 255] == 0)
    # How many pixels are
    true_positives = np.count_nonzero(copy_data == 255)
    #total = false_negatives + true_positives
    if true_positives + false_positives:
        precision = float(true_positives) / (true_positives + false_positives)
    else:
        precision = 0
    if true_positives + false_negatives:
        recall = float(true_positives) / (true_positives + false_negatives)
    else:
        recall = 0
    if recall == 0 or precision == 0:
        f_measure = 0
    else:
        f_measure = float(2 * float((precision * recall) / (precision + recall)))
    return non_zero, true_positives, false_positives, true_negatives, false_negatives

def average_contacts(contacts):
    num_contacts = len(contacts)
    empty_array = np.zeros((50, 100, num_contacts)) # _this should fit ANY_tHING
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        empty_array[0:nx, 0:ny, index] = contact # dump the array in the empty one
    average_array = np.mean(empty_array, axis=2)
    max_x, max_y = np.max(np.nonzero(average_array)[0]), np.max(np.nonzero(average_array)[1])
    average_array = average_array[0:max_x+1, 0:max_y+1]
    return average_array


def calculate_cop(data):
    copx, copy = [], []
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
                copx.append(np.round(np.sum(temp_x[:, frame]) / np.sum(data[:, :, frame]), 2))
                copy.append(np.round(np.sum(temp_y[:, frame]) / np.sum(data[:, :, frame]), 2))
    return copx, copy


def scipy_cop(data):
    copx, copy = [], []
    height, width, length = data.shape
    for frame in range(length):
        y, x = scipy.ndimage.measurements.center_of_mass(data[:, :, frame])
        copx.append(x + 1)
        copy.append(y + 1)
    return copx, copy

def get_QPixmap(data, degree, n_max, color_table):
    """
    _this function expects a single frame, it will interpolate/resize it with a given degree and
    return a pixmap
    """
    # Need the sizes before reshaping
    width, height = data.shape
    # _this can be used to interpolate, but it doesn't seem to work entirely correct yet...
    data = cv2.resize(data, (height * degree, width * degree), interpolation=cv2.IN_tER_LINEAR)
    # Normalize the data
    data = normalize(data, n_max)
    # Convert it from numpy to qimage
    qimage = array2qimage(data, color_table)
    # Convert the image to a pixmap
    pixmap = QPixmap.fromImage(qimage)
    # Scale up the image so its better visible
    #self.pixmap = self.pixmap.scaled(self.degree * self.height, self.degree * self.width,
    #                                 Qt.KeepAspectRatio, Qt.Fast_transformation) #Qt.Smooth_transformation
    return pixmap

def array2qimage(array, color_table):
    """Convert the 2D numpy array  into a 8-bit QImage with a gray
    colormap.  _the first dimension represents the vertical image axis."""
    array = np.require(array, np.uint8, 'C')
    width, height = array.shape
    result = QImage(array.data, height, width, QImage.Format_Indexed8)
    result.ndarray = array
    # Use the default one from this library
    result.setColor_table(color_table)
    # Convert it to RGB32
    result = result.convert_toFormat(QImage.Format_RGB32)
    return result

def interpolate_rgb(startColor, startValue, endColor, endValue, actualValue):
    deltaValue = endValue - startValue
    if deltaValue == 0.0:
        return startColor

    multiplier = (actualValue - startValue) / deltaValue

    startRed = (startColor >> 16) & 0xff
    endRed = (endColor >> 16) & 0xff
    deltaRed = endRed - startRed
    red = startRed + (deltaRed * multiplier)

    if deltaRed > 0:
        if red < startRed:
            red = startRed
        elif red > endRed:
            red = endRed
    else:
        if red > startRed:
            red = startRed
        elif red < endRed:
            red = endRed

    startGreen = (startColor >> 8) & 0xff
    endGreen = (endColor >> 8) & 0xff
    deltaGreen = endGreen - startGreen
    green = startGreen + (deltaGreen * multiplier)

    if deltaGreen > 0:
        if green < startGreen:
            green = startGreen
        elif green > endGreen:
            green = endGreen
    else:
        if green > startGreen:
            green = startGreen
        elif green < endGreen:
            green = endGreen

    startBlue = startColor & 0xff
    endBlue = endColor & 0xff
    deltaBlue = endBlue - startBlue
    blue = startBlue + (deltaBlue * multiplier)

    if deltaBlue > 0:
        if blue < startBlue:
            blue = startBlue
        elif blue > endBlue:
            blue = endBlue
    else:
        if blue > startBlue:
            blue = startBlue
        elif blue < endBlue:
            blue = endBlue

    return qRgb(red, green, blue)


class ImageColor_table():
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
        color_table = [self.black for i in range(255)]
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


def ColorMap():
    import matplotlib

    my_color_map = {'blue': [(0.0, 0.0, 0.0), (0.12, 1.0, 1.0), (0.44, 0.0, 0.0), (0.76000000000000001, 0.0, 0.0),
                        (0.92000000000000004, 0.0, 0.0), (1, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0), (0.12, 0.29999999999999999, 0.29999999999999999), (0.44, 1.0, 1.0),
                         (0.76000000000000001, 0.90000000000000002, 0.90000000000000002),
                         (0.92000000000000004, 0.40000000000000002, 0.40000000000000002), (1, 0.0, 0.0)],
               'red': [(0.0, 0.0, 0.0), (0.12, 0.0, 0.0), (0.44, 0.0, 0.0), (0.76000000000000001, 1.0, 1.0),
                       (0.92000000000000004, 1.0, 1.0), (1, 1.0, 1.0)]}
    new_color_map = matplotlib.colors.LinearSegmentedColormap('my_color_map', my_color_map)
    return new_color_map

def create_hex_colormap():
	import matplotlib.colors as colors
	
	my_color_map = {'blue': [(0.0, 0.0, 0.0), (0.12, 1.0, 1.0), (0.44, 0.0, 0.0), (0.76000000000000001, 0.0, 0.0),
                        (0.92000000000000004, 0.0, 0.0), (1, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0), (0.12, 0.29999999999999999, 0.29999999999999999), (0.44, 1.0, 1.0),
                         (0.76000000000000001, 0.90000000000000002, 0.90000000000000002),
                         (0.92000000000000004, 0.40000000000000002, 0.40000000000000002), (1, 0.0, 0.0)],
               'red': [(0.0, 0.0, 0.0), (0.12, 0.0, 0.0), (0.44, 0.0, 0.0), (0.76000000000000001, 1.0, 1.0),
                       (0.92000000000000004, 1.0, 1.0), (1, 1.0, 1.0)]}
					   
	red = colors.makeMappingArray(256, my_color_map['red'])
	green = colors.makeMappingArray(256, my_color_map['green'])
	blue = colors.makeMappingArray(256, my_color_map['blue'])
	color_scale = np.array(zip(red, green, blue))
	
	def convert_to_hex(color_scale):
		list_of_hex = []
		for colors in color_scale:
			hex_string = '#%02x%02x%02x' % tuple([np.round(val * 255) for val in colors])
			list_of_hex.append(hex_string)
		return list_of_hex  
		
	return convert_to_hex(color_scale)

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


