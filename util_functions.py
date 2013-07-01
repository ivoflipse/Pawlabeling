import numpy as np
import math
import cv2

def touches_edges(data, data_slice):
    ny, nx, nt = np.shape(data)
    y, x, t = data_slice
    xtouch = (x.start == 0) or (x.stop == nx)
    ytouch = (y.start == 0) or (y.stop == ny)
    ttouch = (t.stop == nt)
    return xtouch or ytouch or ttouch


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


def PAA(data, step_size=3):
    return [np.mean(chunk) for chunk in chunks(data, step_size)]


def map_to_string(PAA, alphabet_size):
    """
    I'm not sure whether using len here is appropriate
    Shouldn't I be using shape and testing if we even have the appropriate format?
    """
    result = np.zeros((len(PAA)))

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
    for i in range(len(PAA)):
        result[i] = np.sum((cut_points <= PAA[i]))
    return result


def timeseries2symbol(data, N, n, alphabet_size):
    """
    N = data_len or sliding window
    n = nseg
    When calculating the ratio N / n, make sure one of them is a float!
    Use as: current_string = timeseries2symbol(data, data_len, nseg, alphabet_size)
    """
    if alphabet_size > 20:
        print "Alphabet is too large!"

    win_size = int(math.floor(N / n))

    # If N == data_len, then this will only be done once
    # So then we don't use a sliding window
    for i in range(len(data) - (N - 1)):
    # Slice the data
        sub_section = data[i:i + N]
        # Z normalize it
        # Turned off for now, since its already applied, but then to the entire dataset
        sub_section = (sub_section - np.mean(sub_section))/ np.std(sub_section)

        # If the data is as long as the number of segments, we don't have to PAA
        if N == n:
            PAA = sub_section
        else:
            # Check if we have the right number of segments
            if (N / float(n) - math.floor(N / n)): # If this is not zero, the ratio is off
                # Tile the sub_sections
                temp = np.tile(data[:, None], (n))
                # Unroll the subsections from N x n to 1 x (N*n)
                expanded_sub_section = np.reshape(temp, (1, N * n))
                PAA = np.mean(np.reshape(expanded_sub_section, (n, N)), axis=1)
            else:
                # This last part can probably be rewritten, so I only have to PAA once.
                # But we'll wait until we know it actually works!
                PAA = np.mean(np.reshape(sub_section, (n, win_size)), axis=1)

    current_string = map_to_string(PAA, alphabet_size)
    # Here follow so steps related to pointers, but I have no idea what for
    # They also delete the first item from symbolic_data, which is being returned
    # But I think that's only important if you really use the sliding window in some way
    return current_string


def saxify(data, n=10, alphabet_size=4, plot_results=False, axes=None):
    """
    data is expected to be a 1D time serie
    n = number of segments
    alphabet_size has to be 2 < size < 20, defines how the number of intervals in Y
    Assumes numpy is imported as np
    """
    N = len(data)
    win_size = int(math.floor(N / n))
    # Do I want to Z-normalize?
    data = (data - np.mean(data)) / np.std(data)

    # Check if we have the right number of segments
    if N / float(n) - math.floor(N / n):  # If this is not zero, the ratio is off
        # Tile the sub_sections
        temp = np.tile(data[:, None], n)
        # Unroll the subsections from N x n to 1 x (N*n)
        expanded_sub_section = np.reshape(temp, (1, N * n))
        PAA = np.mean(np.reshape(expanded_sub_section, (n, N)), axis=1)
    else:
        PAA = np.mean(np.reshape(data, (n, win_size)), axis=1)

    # I might strip out N, because I don't use sliding windows
    current_string = timeseries2symbol(data, N, n, alphabet_size)
    symbols = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
               'v', 'w', 'x', 'y', 'z']

    new_string = "".join([symbols[int(current_string[i]) - 1] for i in range(n)])
    if plot_results:
        color = ['g', 'y', 'm', 'c']
        # Rescale the piecewise data
        PAA_plot = np.reshape(np.tile(PAA[:, None], win_size), (win_size * n))  # data_len
        axes.plot(PAA_plot, 'r')

        for i in range(n):
            x_start = i * win_size
            x_end = x_start + win_size
            x_mid = x_start + (x_end - x_start) / 2
            # Subtract one, because we start indexing from zero
            letter = int(current_string[i]) - 1
            colorIndex = int(letter % len(color))
            axes.plot(range(x_start, x_end), PAA_plot[x_start:x_end], color=color[colorIndex], linewidth=3)
            axes.text(x_mid, PAA_plot[x_start], new_string[i], fontsize=14)

    # Actually this returns the numeric version!
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
        print "Error: strings must have equal length!"
        return

    # Wait does this check whether any of the chars
    # Matlab: if (any(str1 > alphabet_size) | any(str2 > alphabet_size))
    if any(str1 > alphabet_size) or any(str2 > alphabet_size):
        print "Error: some symbols in the string exceed the alphabet_size!"
        return

    distances = calc_distances(str1, str2, alphabet_size)
    dist = np.sqrt(compression_ratio * sum(np.diagonal(distances)))

    return dist


def interpolateFrame(data, degree):
    """
    interpolateFrame interpolates one frame for a given degree. Don't insert a 3D array!
    """
    from scipy.ndimage import map_coordinates

    ny, nx = np.shape(data)
    STD_NUMX = nx * degree
    STD_NUMY = ny * degree
    # Based on a scientific guess
    # Make a 20x20 grid to resample the paw pressure values onto
    #STD_NUMX, STD_NUMY = 20, 20
    xi = np.linspace(0, nx, STD_NUMX)
    yi = np.linspace(0, ny, STD_NUMY)
    xi, yi = np.meshgrid(xi, yi)
    # Resample the values onto the 20x20 grid
    coords = np.vstack([yi.flatten(), xi.flatten()])
    zi = map_coordinates(data, coords)
    zi = zi.reshape(STD_NUMY, STD_NUMX)
    return zi


def distance_between_centers(center1, center2):
    x1, y1 = center1
    x2, y2 = center2
    dx = x1 - x2
    dy = y1 - y2
    return (dx * dx + dy * dy) ** 0.5


def contour_from_max_of_max(max_of_max):
    copy_data = np.copy(max_of_max)
    _, copy_data = cv2.threshold(copy_data, 0.0, 1, cv2.THRESH_BINARY)
    new_data = copy_data.astype('uint8')
    contourList, _ = cv2.findContours(new_data, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return contourList


def distance_to_contour(center, contour_list):
    distances = []
    for contour in contour_list:
        for coord in contour:
            dist = distance_between_centers(center, coord[0])
            distances.append(dist)
    return distances


def scipy_cop(data):
    from scipy.ndimage.measurements import center_of_mass

    copx, copy = [], []
    height, width, length = data.shape
    for frame in range(length):
        y, x = center_of_mass(data[:, :, frame])
        copx.append(x + 1)
        copy.append(y + 1)
    return copx, copy


















