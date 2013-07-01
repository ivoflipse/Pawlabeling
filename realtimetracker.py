# -*- coding: utf-8 -*-
"""
Created on Wed Jul 11 13:11:39 2012

@author: Ivo
"""

import cv2
import heapq

import numpy as np
import matplotlib.pyplot as plt
import scipy.stats
import scipy.ndimage

import utility

class Contact():
    """
    This class has only one real function and that's to take a contact and create some
    attributes that my viewer depends upon. These are a contourList that contains all the contours
    and the dimensions + center of the bounding box of the entire contact
    """

    def __init__(self, contact):
        self.frames = sorted(contact.keys())
        self.contourList = {}
        for frame in self.frames:
            self.contourList[frame] = contact[frame]
        center, minx, maxx, miny, maxy = updateBoundingBox(contact)
        self.totalminx, self.totalmaxx = minx, maxx
        self.totalminy, self.totalmaxy = miny, maxy
        self.totalcentroid = center

    def __str__(self):
        for frame in self.frames:
            print "Frame %s", frame
            for index, contour in enumerate(self.contourList[frame]):
                print "Contour %s: %s" % (index, "".join([str(c) for c in contour]))


def calculateDistance(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))


def calculateBoundingBox(contour):
    """
    This function calculates the bounding box based on an individual contour
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
    minx = x - xdist
    maxx = x + xdist
    miny = y - ydist
    maxy = y + ydist
    return center, minx, maxx, miny, maxy


def updateBoundingBox(contact):
    """
    Given a contact, it will iterate through all the frames and calculate the bounding box
    It then compares the dimensions of the bounding box to determine the total shape of that
    contacts bounding box
    """
    # Don't accept empty contacts
    assert len(contact) > 0

    totalminx, totalmaxx = None, None
    totalminy, totalmaxy = None, None

    # For each contour, get the sizes
    for frame in contact.keys():
        for contour in contact[frame]:
        #        for contour in maxContours:
            center, minx, maxx, miny, maxy = calculateBoundingBox(contour)
            if totalminx is None:
                totalminx = minx
                totalmaxx = maxx
                totalminy = miny
                totalmaxy = maxy

            if minx < totalminx:
                totalminx = minx
            if maxx > totalmaxx:
                totalmaxx = maxx
            if miny < totalminy:
                totalminy = miny
            if maxy > totalmaxy:
                totalmaxy = maxy

    totalcentroid = ((totalmaxx + totalminx) / 2, (totalmaxy + totalminy) / 2)
    return totalcentroid, totalminx, totalmaxx, totalminy, totalmaxy


def calcTemporalSpatialVariables(contacts):
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
        center, minx, maxx, miny, maxy = updateBoundingBox(contact)
        centers.append(center)

        width = maxx - minx
        if width > 2:
            sides.append(width)
        height = maxy - miny
        if height > 2:
            sides.append(height)

        surface = width * height
        surfaces.append(surface)

        lengths.append(len(contact.keys()))
    return sides, centers, surfaces, lengths


def mergeContours(contact1, contact2):
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


def find_regions_3D(Array):
    """
    Borrowed from Stack Overflow
    """
    x_dim = np.size(Array, 0)
    y_dim = np.size(Array, 1)
    z_dim = np.size(Array, 2)
    array_region = np.zeros((x_dim, y_dim, z_dim), )
    equivalences = {}
    n_regions = 0
    #first pass. find regions.
    ind = np.where(Array > 0.0)
    for x, y, z in zip(ind[0], ind[1], ind[2]):
        # get the region number from all surrounding cells including diagnols (27) or create new region                        
        xMin = max(x - 1, 0)
        xMax = min(x + 1, x_dim - 1)
        yMin = max(y - 1, 0)
        yMax = min(y + 1, y_dim - 1)
        zMin = max(z - 1, 0)
        zMax = min(z + 1, z_dim - 1)
        max_region = array_region[xMin:xMax + 1, yMin:yMax + 1, zMin:zMax + 1].max()
        if max_region > 0:
            #a neighbour already has a region, new region is the smallest > 0
            #new_region = min(filter(lambda i: i > 0, array_region[xMin:xMax + 1, yMin:yMax + 1, zMin:zMax + 1].ravel()))
            new_region = array_region[xMin:xMax + 1, yMin:yMax + 1, zMin:zMax + 1]
            new_region = min(new_region[new_region > 0])
            #update equivalences
            if max_region > new_region:
                if max_region in equivalences:
                    equivalences[max_region].add(new_region)
                else:
                    equivalences[max_region] = set((new_region,))
        else:
            n_regions += 1
            new_region = n_regions
        array_region[x, y, z] = new_region
        #Scan Array again, assigning all equivalent regions the same region value.
    for x, y, z in zip(ind[0], ind[1], ind[2]):
        r = array_region[x, y, z]
        while r in equivalences:
            r = min(equivalences[r])
        array_region[x, y, z] = r
        #return list(regions.itervalues())
    return array_region


def trackContours_connected_components(data, euclideanDistance=15, frameThreshold=5):
    connected_components = find_regions_3D(data)
    # Find the contours in this frame
    rows, cols, numFrames = data.shape
    # We iterate through the number of contacts
    numContacts = np.unique(connected_components)
    contacts = [{} for i in numContacts]
    for frame in range(numFrames):
        for idx, index in enumerate(numContacts):
            index = int(index)
            copy_data = connected_components[:, :, frame].T #* 1.
            copy_data *= (copy_data == index)
            _, copy_data = cv2.threshold(copy_data.astype(np.float32), 0.0, 1, cv2.THRESH_BINARY)
            contourList, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if contourList:
                contacts[idx][frame] = []
                for contour in contourList:
                    contacts[idx][frame].append(contour)
    contacts = [contact for contact in contacts if len(contact) > 0]
    return contacts


def convertBoolToRange(X):
    x_range = []
    # We use a set, so I can add dupes, better be safe than sorry
    contact = set()
    # Iterate through the list
    for idx, (x, y) in enumerate(zip(X[:-1], X[1:])):
        # If the current index is True, add it to contact
        if y - x == 1:
            contact.add(x)
            # If x has become False and we have a contact, add it to the range
        if y - x > 1 and contact:
            contact.add(x)
            # We convert it to a list and sort it
            x_range.append(sorted(list(contact)))
            # Reset contact
            contact = set()
            # If we end with something left in contact, add that too
    if contact:
        x_range.append(sorted(list(contact)))

    return x_range


def trackContours_Jurgen(data, euclideanDistance, frameThreshold):
    results = find_regions((0, 0, 0, 0, 0, 0), data)
    contacts = []
    for coordinates, slice in results:
        contact = {}
        Y0, Y1, X0, X1, Z0, Z1 = coordinates
        # Create an empty copy of data
        newData = np.zeros_like(data)
        # Replace a part of the data with a slice of the data
        newData[Y0:Y1, X0:X1, Z0:Z1] += data[Y0:Y1, X0:X1, Z0:Z1]
        # We're going to find contours in the raw data
        for frame in range(Z0, Z1):
            # Threshold the data
            _, copy_data = cv2.threshold(newData[:, :, frame].T, 0.0, 1, cv2.THRESH_BINARY)
            # Find the contours
            contourList, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if contourList:
                # Add all the contours to the contact
                contact[frame] = []
                for contour in contourList:
                    contact[frame].append(contour)
                    # Add the contact to contacts
        contacts.append(contact)
    return contacts


def find_regions(coordinates, data):
    height, width, duration = data.shape
    # Frame of reference of this slice
    Y0, Y1, X0, X1, Z0, Z1 = coordinates
    # Get the indices of the pixels that are nonzero
    # We convert it to a set to remove dupes, convert it back to a ilst
    # So we can walk through it in sorted order
    Y, X, Z = data.nonzero()
    Y = sorted(list(set(Y)))
    X = sorted(list(set(X)))
    Z = sorted(list(set(Z)))

    # Split it up if there's a gap
    x_range = convertBoolToRange(X)
    y_range = convertBoolToRange(Y)
    z_range = convertBoolToRange(Z)

    # Here we enumerate all possible combinations between the different ranges
    # The result gets put into result
    result = []
    for K in z_range:
        # Get the first and last values of the slice
        z0, z1 = K[0], K[-1] + 2
        if z1 > duration: z1 = duration
        for I in x_range:
            x0, x1 = I[0], I[-1] + 2
            if x1 > duration: x1 = width
            for J in y_range:
                y0, y1 = J[0], J[-1] + 2
                if y1 > duration: y1 = height
                #Block3D block <- <Combine x_range[I], y_range[J] and z_range[K]>
                # Add one because of how Python slices
                slice = data[y0:y1, x0:x1, z0:z1]
                # Sorry, but its useless to add empty slices
                if np.max(slice) > 0.0:
                    #<Append block to result>
                    # Update the coordinates
                    newCoords = (Y0 + y0, Y0 + y1, X0 + x0, X0 + x1, Z0 + z0, Z0 + z1)
                    result.append((newCoords, slice))

    # If we don't have any result, this branch is dead
    if not result:
        return None

    # If I understand it correctly, we first create all possible slices from the data where there's
    # a contact. Then we recursively put those through find_regions. If it won't find anything,
    # we skip it, else if we find multiple slices, we try splitting it up, if we find one, we return it
    if len(result) > 1:
        # This should be a block3D, so I presume we slice and dice the data?
        split = []
        for coords, b in result:
            # Recursive call to find_regions on block b
            slices = find_regions(coords, b) # If we don't find anything, we return None
            if slices is not None:
                for slice in slices:
                    split.append(slice)
        result = split
        return result
    else:
        # Check if we could still resize the coordinates
        coords, slice = result[0] # slice name shadows builtin!
        if coords != coordinates:
            return find_regions(coords, slice)
            # Else just return the first element from result
        return result


# Bounding box tracker
def trackContours_hybrid(data, euclideanDistance, frameThreshold):
    results = find_regions((0, 0, 0, 0, 0, 0), data)
    height, width, duration = data.shape
    contacts = []
    for coordinates, slice in results:
        Y0, Y1, X0, X1, Z0, Z1 = coordinates
        # Create an empty copy of data
        newData = np.zeros_like(data)
        # Replace a part of the data with a slice of the data
        newData[Y0:Y1, X0:X1, Z0:Z1] += data[Y0:Y1, X0:X1, Z0:Z1]
        # Lets see if its faster to update the contours or pass it a fake slice from the data
        contactList = trackContours_graph(newData, euclideanDistance, frameThreshold)
        for contact in contactList:
            contacts.append(contact)

    mergeContacts = False
    if mergeContacts:
        # The two functions below have been incorporated into mergingContacts
        # Based on all the results, we try one more iteration to merge any remaining contacts
        # Calculate the frame threshold required for merging
        #frameThreshold = calcFrameThreshold(contacts, frameThreshold)
        # Calculate the euclidean distance based on the median size of the contacts
        #euclideanDistance = calcEuclideanDistance(contacts)
        contacts = mergingContacts_2(contacts)
    return contacts


def closestContact(contact1, contact2, center1, euclideanDistance):
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
    frames = contact1.keys()
    minFrame, maxFrame = min(frames), max(frames)
    # This makes sure it checks if there's nothing close in the neighboring frame
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


def mergingContacts(contacts):
    """
    We compare each contact with the rest, if the distance between the centers of both
    contacts is <= the euclidean distance, then we check if they also made contact during the
    same frames. This ensures that only contours that are in each others vicinity for a sufficient
    amount of frames are considered for merging. Just naively merging based on distance would
    cause problems if dogs place the paws too close too each other.
    This will fail if the dogs paws are close for more frames than the threshold.
    """

    # Get the important temporal spatial variables
    sides, centerList, surfaces, lengths = calcTemporalSpatialVariables(contacts)
    # Get their averages and adjust them when needed
    frameThreshold = np.mean(lengths) * 0.5
    euclideanDistance = np.mean(sides)
    averageSurface = np.mean(surfaces) * 0.25
    # Initialize two dictionaries for calculating the Minimal Spanning Tree
    leaders = {}
    clusters = {}
    # This list forms the heap to which we'll add all edges
    edges = []
    for index1, contact1 in enumerate(contacts):
        clusters[index1] = set([index1])
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
                        # If the overlap is larger than the frameThreshold we always merge
                        if overlap >= frameThreshold:
                            merge = True
                            value = (euclideanDistance - distance) * overlap
                        # If the first contact is too short, but we have overlap nonetheless,
                        # we also merge, we'll deal with picking the best value later
                        elif length1 <= frameThreshold and overlap:
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
                        if length1 <= frameThreshold and not overlap:
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
    # This is where we actually merge the contacts in 
    # each cluster
    for key, indices in clusters.items():
        newContact = {}
        for index in indices:
            contact = contacts[index]
            mergeContours(newContact, contact)
        newContacts.append(newContact)

    return newContacts


def findContours(data):
    # Dictionary to fill with results
    contourDict = {}
    # Find the contours in this frame
    rows, cols, numFrames = data.shape
    for frame in range(numFrames):
        # Threshold the data
        copy_data = data[:, :, frame].T * 1.
        _, copy_data = cv2.threshold(copy_data, 0.0, 1, cv2.THRESH_BINARY)
        # The astype conversion here is quite expensive! 
        contourList, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contourList:
            contourDict[frame] = contourList
    return contourDict

# I'm trying to get this working in Cython
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
                            shortContour, longContour = contour1, contour2
                        else:
                            shortContour, longContour = contour2, contour1

                        # Compare the first two coordinates, if they aren't even close. Don't bother
                        coord1 = shortContour[0]
                        coord2 = longContour[0]
                        distance = coord1[0][0] - coord2[0][0]
                        # Taking a safe margin
                        if distance <= 2 * euclideanDistance:
                            match = False
                            # We iterate through all the coordinates in the shortcontour and test if
                            # they fall within or on the border of the larger contour. We stop comparing
                            # ones we've found a match
                            for coords in shortContour:
                                if not match:
                                    coords = (coords[0][0], coords[0][1])
                                    if cv2.pointPolygonTest(longContour, coords, 0) > -1.0:
                                        match = True
                                        # Create a bi-directional edge between the two keys
                                        G[(frame, index1)].add((f, index2))
                                        G[(f, index2)].add((frame, index1))
                                        # Perhaps this could be sped up, by keeping a cache of centroids of paws
                                        # then check if there was a paw in the same place on the last frame
                                        # if so, link them and stop looking
    return G


def searchGraph(G, contourDict):
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


def trackContours_graph(data):
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
    contourDict = findContours(data)
    # Create a graph by connecting contours that have overlap with contours in the 
    # previous frame
    G = createGraph(contourDict, euclideanDistance=15)
    # Search through the graph for all connected components
    contacts = searchGraph(G, contourDict)
    # Merge connected components using a minimal spanning tree, where
    # the contacts larger than the threshold are only allowed to merge if they
    # have overlap that's >= than the frame threshold
    contacts = mergingContacts(contacts)
    return contacts


def find_paws(data, smooth_radius=5, threshold=0.0001):
    data = scipy.ndimage.uniform_filter(data, smooth_radius)
    thresh = data > threshold
    filled = scipy.ndimage.morphology.binary_fill_holes(thresh)
    coded_paws, num_paws = scipy.ndimage.label(filled)
    data_slices = scipy.ndimage.find_objects(coded_paws)
    return data_slices


def trackContours_findObjects(data, euclideanDistance, frameThreshold):
    results = find_paws(data, smooth_radius=3)
    contacts = []
    for slice in results:
        contact = {}
        x, y, z = slice
        # Create an empty copy of data
        newData = np.zeros_like(data)
        # Replace a part of the data with a slice of the data
        newData[slice] += data[slice]
        # We're going to find contours in the raw data
        for frame in range(z.start, z.stop):
            # Threshold the data
            _, copy_data = cv2.threshold(newData[:, :, frame].T, 0.0, 1, cv2.THRESH_BINARY)
            # Find the contours
            contourList, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if contourList:
                # Add all the contours to the contact
                contact[frame] = []
                for contour in contourList:
                    contact[frame].append(contour)
                    # Add the contact to contacts
        contacts.append(contact)
    return contacts



def main():
    # Plot the bounding boxes around the paws on the MoM data
    colors = ['b', 'g', 'r', 'k', 'm', 'y', 'c']
    import gzip
    infile = gzip.open("normal_measurement.gz","rb")
    data = utility.load(infile, padding=True)

    copy_data = data.copy()
    non_zero = np.count_nonzero(data)

    contacts = trackContours_graph(data)
    print len(contacts)
    print [len(contact) for contact in contacts]
    newContacts = [Contact(contact) for contact in contacts]

    fig = plt.figure()
    axes = fig.add_subplot(111)
    for index, contact in enumerate(contacts):
        center, minx, maxx, miny, maxy = updateBoundingBox(contact)
        xline = [minx, maxx, maxx, minx, minx]
        yline = [miny, miny, maxy, maxy, miny]
        axes.plot(xline, yline, color=colors[index % len(colors)], linewidth=3)
    axes.imshow(data.max(axis=2).T)
    plt.show()

if __name__ == '__main__':
    main()



