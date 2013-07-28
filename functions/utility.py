from PySide import QtGui, QtCore
import numpy as np
import logging
from functions.pubsub import pub

logger = logging.getLogger("logger")


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
        self.frames = [x for x in range(contact["min_z"], contact["max_z"] + 1)]
        self.width = contact["width"]
        self.height = contact["height"]
        self.length = contact["length"]
        self.total_min_x = contact["min_x"]
        self.total_max_x = contact["max_x"]
        self.total_min_y = contact["min_y"]
        self.total_max_y = contact["max_y"]
        self.total_centroid = (contact["center_x"], contact["center_y"])

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


def update_bounding_box(contact):
    """
    Given a contact, it will iterate through all the frames and calculate the bounding box
    It then compares the dimensions of the bounding box to determine the total shape of that
    contacts bounding box
    """
    import cv2
    # Don't accept empty contacts
    assert len(contact) > 0

    total_min_x, total_max_x = float("inf"), float("-inf")
    total_min_y, total_max_y = float("inf"), float("-inf")

    # For each contour, get the sizes
    for frame in list(contact.keys()):
        for contour in contact[frame]:
            x, y, width, height = cv2.boundingRect(contour)
            if x < total_min_x:
                total_min_x = x
            max_x = x + width
            if max_x > total_max_x:
                total_max_x = max_x
            if y < total_min_y:
                total_min_y = y
            max_y = y + height
            if max_y > total_max_y:
                total_max_y = max_y

    total_centroid = ((total_max_x + total_min_x) / 2, (total_max_y + total_min_y) / 2)
    return total_centroid, total_min_x, total_max_x, total_min_y, total_max_y


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


def normalize_paw_data(paw_data):
    mx = 100
    my = 100

    x, y, z = paw_data.shape
    offset_x, offset_y = int((mx - x) / 2), int((my - y) / 2)
    average_slice = np.zeros((mx, my))
    average_slice[offset_x:offset_x + x, offset_y:offset_y + y] = paw_data.max(axis=2)
    return average_slice


def calculate_average_data(paw_data):
    mx = 100
    my = 100
    mz = 200
    # Get the max shape
    for data in paw_data:
        x, y, z = data.shape
        if x > mx:
            mx = x
        if y > my:
            my = y
        if z > mz:
            mz = z

    # Pad everything with zeros
    empty_slice = np.zeros((mx, my, mz))
    num_paws = len(paw_data)
    padded_data = np.zeros((num_paws, mx, my, mz))
    for index, data in enumerate(paw_data):
        x, y, z = data.shape
        offset_x = int((mx - x) / 2)
        offset_y = int((my - y) / 2)
        # Create a deep copy of the empty array to fill up
        padded_slice = empty_slice.copy()
        padded_slice[offset_x:offset_x + x, offset_y:offset_y + y, 0:z] = data
        padded_data[index,:,:,:] = padded_slice

    return padded_data


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

    x, y, z = data.shape
    # Check bounds
    if min_x1 < 0:
        min_x1 = 0
    if max_x1 > x:
        max_x1 = x
    if min_y1 < 0:
        min_y1 = 0
    if max_y1 > y:
        max_y1 = y

    return newData[min_x1:max_x1, min_y1:max_y1, min_z:max_z]


def contour_to_polygon(contour, degree, offset_x=0, offset_y=0):
    # Loop through the contour, create a polygon out of it
    polygon = []
    coordinates = [[0][0]]  # Dummy coordinate
    for coordinates in contour:
        # Convert the points from the contour to QPointFs and add them to the list
        # The offset is used when you only display a slice, so you basically move the origin
        polygon.append(QtCore.QPointF((coordinates[0][0] - offset_x) * degree, (coordinates[0][1] - offset_y) * degree))
        # If the contour has only a single point, add another point, that's right beside it
    if len(contour) == 1:
        polygon.append(QtCore.QPointF((coordinates[0][0] + 1 - offset_x) * degree,
                                      (
                                          coordinates[0][
                                              1] + 1 - offset_y) * degree)) # Pray this doesn't go out of bounds!
    return QtGui.QPolygonF(polygon)


def contour_to_lines(contour):
    x = []
    y = []
    for point in contour:
        x.append(point[0][0])
        y.append(point[0][1])
    return x, y


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


def normalize(array, n_max):
    """
    This rescales all the values to be between 0-255
    """
    # If we have a non-zero offset, subtract the minimum
    if n_max == 0:
        return array

    # Make sure all negative values get set to zero
    array[array < 0] = 0
    # Get the scaling factor, so everything fits into a uint8
    scale = 255. / n_max
    array *= scale
    return array


def array_to_qimage(array, color_table):
    """Convert the 2D numpy array  into a 8-bit QImage with a gray
    colormap.  The first dimension represents the vertical image axis."""
    array = np.require(array, np.uint8, 'C')
    width, height = array.shape
    result = QtGui.QImage(array.data, height, width, QtGui.QImage.Format_Indexed8)
    result.ndarray = array
    # Use the default one from this library
    result.setColorTable(color_table)
    # Convert it to RGB32
    result = result.convertToFormat(QtGui.QImage.Format_RGB32)
    return result


def get_QPixmap(data, degree, n_max, color_table, interpolation="cubic"):
    """
    This function expects a single frame, it will interpolate/resize it with a given degree and
    return a pixmap
    """
    import cv2
    # Need the sizes before reshaping
    width, height = data.shape

    if interpolation == "linear":
        interpolation = cv2.INTER_LINEAR
    elif interpolation == "nearest":
        interpolation = cv2.INTER_NEAREST
    elif interpolation == "cubic":
        interpolation = cv2.INTER_CUBIC

    # This can be used to interpolate, but it doesn't seem to work entirely correct yet...
    data = cv2.resize(data, (height * degree, width * degree), interpolation=interpolation)
    # Normalize the data
    data = normalize(data, n_max)
    # Convert it from numpy to qimage
    qimage = array_to_qimage(data, color_table)
    # Convert the image to a pixmap
    pixmap = QtGui.QPixmap.fromImage(qimage)
    # Scale up the image so its better visible
    #self.pixmap = self.pixmap.scaled(self.degree * self.height, self.degree * self.width,
    #                                 Qt.KeepAspectRatio, Qt.Fas.Transformation) #Qt.Smoot.Transformation
    return pixmap


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

    return QtGui.qRgb(red, green, blue)


class ImageColorTable():
    def __init__(self):
        self.black = QtGui.QColor(0, 0, 0).rgb()
        self.lightblue = QtGui.QColor(0, 0, 255).rgb()
        self.blue = QtGui.QColor(0, 0, 255).rgb()
        self.cyan = QtGui.QColor(0, 255, 255).rgb()
        self.green = QtGui.QColor(0, 255, 0).rgb()
        self.yellow = QtGui.QColor(255, 255, 0).rgb()
        self.orange = QtGui.QColor(255, 128, 0).rgb()
        self.red = QtGui.QColor(255, 0, 0).rgb()
        self.white = QtGui.QColor(255, 255, 255).rgb()

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
                    else:
                        logger.warning(
                            "There's an error in your color table. This is likely caused by incorrect normalization")
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
        z_touch = (paw.frames[-1] >= nt)
    return x_touch or y_touch or z_touch


def incomplete_step(data_slice):
    from settings import configuration

    pressure_over_time = np.sum(np.sum(data_slice, axis=0), axis=0)
    max_pressure = np.max(pressure_over_time)
    incomplete = False
    #print max_pressure, configuration.start_force_percentage*max_pressure, pressure_over_time[0], pressure_over_time[-1]
    if (pressure_over_time[0] > (configuration.start_force_percentage * max_pressure) or
                pressure_over_time[-1] > (configuration.end_force_percentage * max_pressure)):
        incomplete = True
    return incomplete


def filter_outliers(data, num_std=2):
    import calculations

    lengths = np.array([d.shape[2] for d in data])
    forces = np.array([np.max(calculations.force_over_time(d)) for d in data])
    pixel_counts = np.array([np.max(calculations.pixel_count_over_time(d)) for d in data])

    # Get mean +/- num_std's * std
    mean_length = np.mean(lengths)
    std_length = np.std(lengths)
    min_std_lengths = mean_length - num_std * std_length
    max_std_lengths = mean_length + num_std * std_length

    mean_forces = np.mean(forces)
    std_forces = np.std(forces)
    min_std_forces = mean_forces - num_std * std_forces
    max_std_forces = mean_forces + num_std * std_forces

    mean_pixel_counts = np.mean(pixel_counts)
    std_pixel_counts = np.std(pixel_counts)
    min_std_pixel_counts = mean_pixel_counts - num_std * std_pixel_counts
    max_std_pixel_counts = mean_pixel_counts + num_std * std_pixel_counts

    new_data = []
    filtered = []
    for index, (l, f, p, d) in enumerate(zip(lengths, forces, pixel_counts, data)):
        if (min_std_lengths < l < max_std_lengths and
                        min_std_forces < f < max_std_forces and
                        min_std_pixel_counts < p < max_std_pixel_counts):
            new_data.append(d)
        else:
            filtered.append(index)

    if filtered:
        # Notify the system which contacts you deleted
        pub.sendMessage("updata_statusbar", status="Removed {} contact(s)".format(len(filtered)))
        logger.info("Removed {} contact(s)".format(len(filtered)))
    else:
        logger.info("No contacts removed")
    return new_data


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
        15: [float("-inf"), -1.5, -1.11, -0.84, -0.62, -0.43, -0.25, -0.08, 0.08, 0.25, 0.43, 0.62, 0.84, 1.11,
             1.5],
        16: [float("-inf"), -1.53, -1.15, -0.89, -0.67, -0.49, -0.32, -0.16, 0, 0.16, 0.32, 0.49, 0.67, 0.89, 1.15,
             1.53],
        17: [float("-inf"), -1.56, -1.19, -0.93, -0.72, -0.54, -0.38, -0.22, -0.07, 0.07, 0.22, 0.38, 0.54, 0.72,
             0.93,
             1.19, 1.56],
        18: [float("-inf"), -1.59, -1.22, -0.97, -0.76, -0.59, -0.43, -0.28, -0.14, 0, 0.14, 0.28, 0.43, 0.59, 0.76,
             0.97,
             1.22, 1.59],
        19: [float("-inf"), -1.62, -1.25, -1, -0.8, -0.63, -0.48, -0.34, -0.2 - 0.07, 0.07, 0.2, 0.34, 0.48, 0.63,
             0.8,
             1,
             1.25, 1.62],
        20: [float("-inf"), -1.64, -1.28, -1.04, -0.84, -0.67, -0.52, -0.39, -0.25, -0.13, 0, 0.13, 0.25, 0.39,
             0.52,
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
        logger.critical("The alphabet size for timeseries2symbol is too large.")

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
        16: [-1.56, -1.19, -0.93, -0.72, -0.54, -0.38, -0.22, -0.07, 0.07, 0.22, 0.38, 0.54, 0.72, 0.93, 1.19,
             1.56],
        17: [-1.59, -1.22, -0.97, -0.76, -0.59, -0.43, -0.28, -0.14, 0, 0.14, 0.28, 0.43, 0.59, 0.76, 0.97, 1.22,
             1.59],
        18: [-1.62, -1.25, -1, -0.8, -0.63, -0.48, -0.34, -0.2 - 0.07, 0.07, 0.2, 0.34, 0.48, 0.63, 0.8, 1, 1.25,
             1.62],
        19: [-1.64, -1.28, -1.04, -0.84, -0.67, -0.52, -0.39, -0.25, -0.13, 0, 0.13, 0.25, 0.39, 0.52, 0.67, 0.84,
             1.04,
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
        logger.critical("min_dist: Strings must have equal length")
        return

    # Wait does this check whether any of the chars
    # Matlab: if (any(str1 > alphabet_size) | any(str2 > alphabet_size))
    if any(str1 > alphabet_size) or any(str2 > alphabet_size):
        logger.critical("min_dist: Some symbols in the string exceed the alphabet_size")
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


