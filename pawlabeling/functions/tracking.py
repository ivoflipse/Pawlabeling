from collections import defaultdict
import cv2

import numpy as np

from ..functions.utility import update_bounding_box
from ..settings import settings


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
    min_frame, max_frame = min(frames), max(frames)
    # This makes sure it checks if there's nothing close in the neighboring frame
    # Shouldn't this be up to the gap?
    # Add more frames
    for f in xrange(1, 6):
        frames.append(min_frame - f)
        frames.append(max_frame + f)
    min_distance = euclidean_distance
    value = 0
    for frame in frames:
        if frame in contact2:
            if contact2[frame]:  # How can there be an empty list in here?
                center2, _, _, _, _ = update_bounding_box({frame: contact2[frame]})
                #distance = np.linalg.norm(np.array(center1) - np.array(center2))
                x1 = center1[0]
                y1 = center1[1]
                x2 = center2[0]
                y2 = center2[1]
                distance = (abs(x1 - x2) ** 2 + abs(y1 - y2) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
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
    cause problems if the contacts are too close too each other.
    This will fail if the contacts are close for more frames than the threshold.
    """
    import heapq

    # Get the important temporal spatial variables
    sides, center_list, surfaces, lengths = calculate_temporal_spatial_variables(contacts)
    # Get their averages and adjust them when needed
    frame_threshold = np.mean(lengths) * settings.settings.tracking_temporal()
    euclidean_distance = np.mean(sides) * settings.settings.tracking_spatial()
    average_surface = np.mean(surfaces) * settings.settings.tracking_surface()
    # Initialize two dictionaries for calculating the Minimal Spanning Tree
    leaders = defaultdict()
    clusters = defaultdict(set)
    # This list forms the heap to which we'll add all edges
    edges = []
    for index1, contact1 in enumerate(contacts):
        clusters[index1] = {index1}
        leaders[index1] = index1

        center1 = center_list[index1]
        frames1 = set(contact1.keys())
        length1 = len(frames1)
        surface1 = surfaces[index1]
        for index2, contact2 in enumerate(contacts):
            if index1 != index2:
                center2 = center_list[index2]
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
                if distance <= euclidean_distance:
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
                            value = (euclidean_distance - distance) * overlap
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
                        elif ratio >= 0.2 and surface1 < average_surface:
                            merge = True
                    # In some cases we don't get a merge because there's no overlap
                    # But still its clear these pixels belong to a contact in adjacent frames
                    # If the gap between the two contacts isn't too large, we'll allow that one too
                    else:
                        if length1 <= frame_threshold and not overlap:
                            gap = min([abs(f1 - f2) for f1 in frames1 for f2 in frames2])
                            if gap < 5:  # I changed it to 5, which may or may not work
                                merge = True
                                # If we've found a merge, we'll add it to the heap
                    if merge:
                    # We use two different values for large and short contacts
                        # here we check whether we should calculate a different value
                        if not value:
                            # For short contacts we calculate the average distance to the contact
                            # Which seems to be much more reliable, yet is computationally more expensive
                            value = closest_contact(contact1, contact2, center1, euclidean_distance)
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
    for key, indices in list(clusters.iteritems()):
        new_contact = defaultdict(list)
        for index in indices:
            contact = contacts[index]
            merge_contours(new_contact, contact)
        new_contacts.append(new_contact)

    return new_contacts


def find_contours(data):
    # Dictionary to fill with results
    contour_dict = defaultdict()
    # Find the contours in this frame
    rows, cols, num_frames = data.shape
    for frame in xrange(num_frames):
        copy_data = data[:, :, frame].T * 1.
        # Threshold the measurement_data
        _, copy_data = cv2.threshold(copy_data, 0.0, 1, cv2.THRESH_BINARY)
        # The astype conversion here is quite expensive!
        # Also replaced # CHAIN_APPROX_NONE with CHAIN APPROX SIMPLE
        contour_list, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contour_list:
            contour_dict[frame] = contour_list
    return contour_dict


def create_graph(contour_dict, euclidean_distance=15):
    # Create a graph
    graph = defaultdict(set)
    # Now go through the contour_dict and for each contour, check if there's a matching contour in the adjacent frame
    for frame in contour_dict:
        contours = contour_dict[frame]
        for index1, contour1 in enumerate(contours):
            # Get the contours from the previous frame
            for f in [frame - 1]:
                if f in contour_dict:
                    other_contours = contour_dict[f]
                    # Iterate through the contacts in the adjacent frame
                    for index2, contour2 in enumerate(other_contours):
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
                        if distance <= 2 * euclidean_distance:
                            match = False
                            # We iterate through all the coordinates in the short contour and test if
                            # they fall within or on the border of the larger contour. We stop comparing
                            # ones we've found a match
                            for coordinates in short_contour:
                                if not match:
                                    coordinates = (coordinates[0][0], coordinates[0][1])
                                    if cv2.pointPolygonTest(long_contour, coordinates, 0) > -1.0:
                                        match = True
                                        # Create a bi-directional edge between the two keys
                                        graph[(frame, index1)].add((f, index2))
                                        graph[(f, index2)].add((frame, index1))
                                        # Perhaps this could be sped up, by keeping a cache of centroids of contacts
                                        # then check if there was a contact in the same place on the last frame
                                        # if so, link them and stop looking
    return graph


def search_graph(graph, contour_dict):
    # Empty list of contacts
    contacts = []
    # Set to keep track of contours we've already visited
    explored = set()
    # Go through all nodes in G and find every node
    # its connected to using BFS
    for key in graph:
        if key not in explored:
            frame, index1 = key
            # Initialize a new contact
            contact = defaultdict(list)
            contact[frame].append(contour_dict[frame][index1])
            explored.add(key)
            nodes = set(graph[key])
            # Keep going until there are no more nodes to explore
            while len(nodes) != 0:
                vertex = nodes.pop()
                if vertex not in explored:
                    f, index2 = vertex
                    contact[f].append(contour_dict[f][index2])
                    # Add vertex's neighbors to nodes
                    for v in graph[vertex]:
                        if v not in explored:
                            nodes.add(v)
                    explored.add(vertex)
                    # When we're done add the contact to the contacts list
            contacts.append(contact)
    return contacts


def track_contours_graph(data):
    """
    This tracking algorithm uses a graph based approach.
    It finds all the contours in each frame, connects them based on whether they have overlap in adjacent frames.
    Then finds connected components using a simple graph search. These resulting connected components might
    be unconnected, yet part of the same contact. So we calculate two threshold based on the average duration and
    width/height of the connected components. These are then used to merge connected components with sufficient overlap.
    """
    # Find all the contours, put them in a dictionary where the keys are the frames
    # and the values are the contours
    contour_dict = find_contours(data)
    # Create a graph by connecting contours that have overlap with contours in the previous frame
    graph = create_graph(contour_dict, euclidean_distance=15)
    # Search through the graph for all connected components
    contacts = search_graph(graph, contour_dict)
    # Merge connected components using a minimal spanning tree, where the contacts larger than the threshold are
    # only allowed to merge if they have overlap that's >= than the frame threshold
    contacts = merging_contacts(contacts)
    return contacts