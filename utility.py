import cv2
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
import scipy.ndimage

class arrowFilter(QObject):
    def eventFilter(self, parent, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                parent.mainWidget.slideToLeft()
                return True
            if event.key() == Qt.Key_Right:
                parent.mainWidget.slideToRight()
                return True
        return False

def standardize_paw(paw, STD_NUMX = 20, STD_NUMY = 20):
    """Standardizes a pawprint onto a STD_NUMYxSTD_NUMX grid. Returns a 1D,
    flattened version of the paw data resample onto this grid."""
    from scipy.ndimage import map_coordinates
    ny, nx = np.shape(paw)
    # Based on a scientific guess
    # Make a 20x20 grid to resample the paw pressure values onto
    #STD_NUMX, STD_NUMY = 20, 20
    xi = np.linspace(0, nx, STD_NUMX)
    yi = np.linspace(0, ny, STD_NUMY)
    xi, yi = np.meshgrid(xi, yi)
    # Resample the values onto the 20x20 grid
    coords = np.vstack([yi.flatten(), xi.flatten()])
    zi = map_coordinates(paw, coords)
    zi = zi.reshape(STD_NUMY,STD_NUMX)

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
    for contactnumber, dat_slice in enumerate(data_slices):
        contactnumber += 1
        ny, nx, nt = np.shape(data[dat_slice])
        offsety, offsetx = int((my-ny)/2), int((mx-nx)/2)
        temparray = np.zeros((my, mx))
        for y in range(ny):
            for x in range(nx):
                temparray[y+offsety, x+offsetx] = data[dat_slice].max(axis=2)[y, x]
        padded[contactnumber] = temparray
    return padded

def average_contacts(contacts):
    numcontacts = len(contacts)
    emptyarray = np.zeros((50, 100, numcontacts)) # This should fit ANYTHING
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        emptyarray[0:nx, 0:ny, index] = contact # dump the array in the empty one
    averagearray = np.mean(emptyarray, axis=2)
    xmax, ymax = np.max(np.nonzero(averagearray)[0]), np.max(np.nonzero(averagearray)[1])
    averagearray = averagearray[0:xmax+1, 0:ymax+1]
    return averagearray

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
    #print "The distance between the start and end is: {}".format(x_distance)
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

    This very crudely goes through the file, and if the line starts with an F splits it
    Then if the first word is Frame, it flips a boolean "frame_number" 
    and parses every line until we hit the closing "}".
    """
    frame_number = None
    dataslices = []
    for line in infile:
        # This should prevent it from splitting every line
        if frame_number:
            if line[0] == 'y':
                line = line.split()
                data.append(line[1:])
                # End of the frame
            if line[0] == '}':
                dataslices.append(np.array(data, dtype=np.float32).T)
                frame_number = None

        if line[0] == 'F':
            line = line.split()
            if line[0] == "Frame" and line[-1] == "{":
                frame_number = line[1]
                data = []
    results = np.dstack(dataslices)
    width, height, length = results.shape
    return results if width > height else results.swapaxes(0, 1)

# This functions is modified from:
# http://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
def load(filename, padding=False):
    """Reads all data in the datafile. Returns an array of times for each
    slice, and a 3D array of pressure data with shape (nx, ny, ntimes)."""
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

# Copied from realtimetracker
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

# Copied from realtimetracker
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


def convertContourToSlice(data, contact):
    # Get the bounding box for the entire contact
    center, minx1, maxx1, miny1, maxy1 = updateBoundingBox(contact)
    frames = sorted(contact.keys())
    minz, maxz = frames[0], frames[-1]
    # Create an empty array that should fit the entire contact
    newData = np.zeros_like(data)
    for frame, contours in contact.items():
        # Pass a single frame dictionary as if it were a contact to get its bounding box
        center, minx, maxx, miny, maxy = updateBoundingBox({frame: contours})
        # We need to slice around the contacts a little wider, I wonder what problems this might cause
        minx, maxx, miny, maxy = int(minx), int(maxx) + 2, int(miny), int(maxy) + 2
        newData[minx:maxx, miny:maxy, frame] = data[minx:maxx, miny:maxy, frame]
    return newData[minx1:maxx1 + 2, miny1:maxy1 + 2, minz:maxz + 1]

def contourToPolygon(contour, degree, offsetx=0, offsety=0):
    # Loop through the contour, create a polygon out of it
    polygon = []
    for coords in contour:
        # Convert the points from the contour to QPointFs and add them to the list
        # The offset is used when you only display a slice, so you basically move the origin
        polygon.append(QPointF((coords[0][0] - offsetx) * degree, (coords[0][1] - offsety) * degree))
        # If the contour has only a single point, add another point, that's right beside it
    if len(contour) == 1:
        polygon.append(QPointF((coords[0][0] + 1 - offsetx) * degree,
            (coords[0][1] + 1 - offsety) * degree)) # Pray this doesn't go out of bounds!
    return QPolygonF(polygon)


def contourToLines(contour):
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
    # Threshold the data to get a binary image
    _, copy_data = cv2.threshold(copy_data, threshold, 1, cv2.THRESH_BINARY)
    # Adding dilation and erosion:
    copy_data = cv2.dilate(copy_data, None, iterations=dilationIterations)
    copy_data = cv2.erode(copy_data, None, iterations=erosionIterations)
    # Find the contours
    contours, _ = cv2.findContours(copy_data.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def changeDilationErosion(data, dilationIterations, erosionIterations):
    data = cv2.dilate(data, None, iterations=dilationIterations)
    data = cv2.erode(data, None, iterations=erosionIterations)
    return data


def normalize(array, nmax):
    """
    This rescales all the values to be between 0-255
    """
    # If we have a non-zero offset, subtract the minimum
    if nmax == 0:
        return array

    scale = 255. / nmax
    array = array * scale

    return array


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


def calculateDetectionRate(data, paws, frame):
    copy_data = np.zeros_like(data, dtype=data.dtype)
    non_zero = np.count_nonzero(data)
    # Loop through all the paws
    for index, paw in enumerate(paws):
        # Check if its active in this frame
        if frame in paw.contourList:
            # For all the contours within this frame
            for cont in paw.contourList[frame]:
                cv2.drawContours(image=copy_data.T, contours=[cont], contourIdx=-1, color=(255, 255, 255), thickness=-1)

    # How many pixels above zero are NOT 255
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

def averagecontacts(contacts):
    numcontacts = len(contacts)
    emptyarray = np.zeros((50, 100, numcontacts)) # This should fit ANYTHING
    for index, contact in enumerate(contacts):
        nx, ny = np.shape(contact)
        emptyarray[0:nx, 0:ny, index] = contact # dump the array in the empty one
    averagearray = np.mean(emptyarray, axis=2)
    xmax, ymax = np.max(np.nonzero(averagearray)[0]), np.max(np.nonzero(averagearray)[1])
    averagearray = averagearray[0:xmax+1, 0:ymax+1]
    return averagearray


def calculate_cop(data):
    copx, copy = [], []
    y, x, z = np.shape(data)
    xcoord, ycoord = np.arange(1, x + 1), np.arange(1, y + 1)
    tempx, tempy = np.zeros((y, z)), np.zeros((x, z))
    for frame in range(z):
        if np.sum(data[:, :, frame]) != 0.0: # Else divide by zero
            for col in range(y):
                tempx[col, frame] = np.sum(data[col, :, frame] * xcoord)
            for row in range(x):
                tempy[row, frame] = np.sum(data[:, row, frame] * ycoord)
            if np.sum(tempx[:, frame]) != 0.0 and np.sum(tempy[:, frame]) != 0.0:
                copx.append(np.round(np.sum(tempx[:, frame]) / np.sum(data[:, :, frame]), 2))
                copy.append(np.round(np.sum(tempy[:, frame]) / np.sum(data[:, :, frame]), 2))
    return copx, copy


def scipy_cop(data):
    copx, copy = [], []
    height, width, length = data.shape
    for frame in range(length):
        y, x = scipy.ndimage.measurements.center_of_mass(data[:, :, frame])
        copx.append(x + 1)
        copy.append(y + 1)
    return copx, copy

def getQPixmap(data, degree, nmax, color_table):
    """
    This function expects a single frame, it will interpolate/resize it with a given degree and
    return a pixmap
    """
    # Need the sizes before reshaping
    width, height = data.shape
    # This can be used to interpolate, but it doesn't seem to work entirely correct yet...
    data = cv2.resize(data, (height * degree, width * degree), interpolation=cv2.INTER_LINEAR)
    # Normalize the data
    data = normalize(data, nmax)
    # Convert it from numpy to qimage
    qimage = array2qimage(data, color_table)
    # Convert the image to a pixmap
    pixmap = QPixmap.fromImage(qimage)
    # Scale up the image so its better visible
    #self.pixmap = self.pixmap.scaled(self.degree * self.height, self.degree * self.width,
    #                                 Qt.KeepAspectRatio, Qt.FastTransformation) #Qt.SmoothTransformation
    return pixmap

def array2qimage(array, color_table):
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

        self.blackThreshold = 0.01
        self.lightblueThreshold = 1.00
        self.blueThreshold = 4.83
        self.cyanThreshold = 10.74
        self.greenThreshold = 21.47
        self.yellowThreshold = 93.94
        self.orangeThreshold = 174.0
        self.redThreshold = 256.0

    def create_colortable(self):
        colortable = [self.black for i in range(255)]
        for val in range(255):
            if val < self.blackThreshold:
                colortable[val] = interpolate_rgb(self.black, self.blackThreshold,
                                                  self.blue, self.blueThreshold, val)
            else:
                if val <= self.yellowThreshold:
                    if val <= self.cyanThreshold:
                        if val <= self.blueThreshold:
                            colortable[val] = interpolate_rgb(self.blue, self.blackThreshold,
                                                              self.lightblue, self.blueThreshold, val)
                        else:
                            colortable[val] = interpolate_rgb(self.lightblue, self.blueThreshold,
                                                              self.cyan, self.cyanThreshold, val)
                    else:
                        if val <= self.greenThreshold:
                            colortable[val] = interpolate_rgb(self.cyan, self.cyanThreshold,
                                                              self.green, self.greenThreshold, val)
                        else:
                            colortable[val] = interpolate_rgb(self.green, self.greenThreshold,
                                                              self.yellow, self.yellowThreshold, val)
                else:
                    if val <= self.orangeThreshold:
                        colortable[val] = interpolate_rgb(self.yellow, self.yellowThreshold,
                                                          self.orange, self.orangeThreshold, val)
                    elif val <= self.redThreshold:
                        colortable[val] = interpolate_rgb(self.orange, self.orangeThreshold,
                                                          self.red, self.redThreshold, val)
        return colortable


def ColorMap():
    import matplotlib

    my_cmap = {'blue': [(0.0, 0.0, 0.0), (0.12, 1.0, 1.0), (0.44, 0.0, 0.0), (0.76000000000000001, 0.0, 0.0),
                        (0.92000000000000004, 0.0, 0.0), (1, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0), (0.12, 0.29999999999999999, 0.29999999999999999), (0.44, 1.0, 1.0),
                         (0.76000000000000001, 0.90000000000000002, 0.90000000000000002),
                         (0.92000000000000004, 0.40000000000000002, 0.40000000000000002), (1, 0.0, 0.0)],
               'red': [(0.0, 0.0, 0.0), (0.12, 0.0, 0.0), (0.44, 0.0, 0.0), (0.76000000000000001, 1.0, 1.0),
                       (0.92000000000000004, 1.0, 1.0), (1, 1.0, 1.0)]}
    new_cmap = matplotlib.colors.LinearSegmentedColormap('mycmap', my_cmap)
    return new_cmap

def create_hex_colormap():
	import matplotlib.colors as colors
	
	my_cmap = {'blue': [(0.0, 0.0, 0.0), (0.12, 1.0, 1.0), (0.44, 0.0, 0.0), (0.76000000000000001, 0.0, 0.0),
                        (0.92000000000000004, 0.0, 0.0), (1, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0), (0.12, 0.29999999999999999, 0.29999999999999999), (0.44, 1.0, 1.0),
                         (0.76000000000000001, 0.90000000000000002, 0.90000000000000002),
                         (0.92000000000000004, 0.40000000000000002, 0.40000000000000002), (1, 0.0, 0.0)],
               'red': [(0.0, 0.0, 0.0), (0.12, 0.0, 0.0), (0.44, 0.0, 0.0), (0.76000000000000001, 1.0, 1.0),
                       (0.92000000000000004, 1.0, 1.0), (1, 1.0, 1.0)]}
					   
	red = colors.makeMappingArray(256, my_cmap['red'])
	green = colors.makeMappingArray(256, my_cmap['green'])
	blue = colors.makeMappingArray(256, my_cmap['blue'])
	colorscale = np.array(zip(red, green, blue))
	
	def convert_to_hex(colorscale):
		list_of_hex = []
		for colors in colorscale:
			hex_string = '#%02x%02x%02x' % tuple([np.round(val * 255) for val in colors])
			list_of_hex.append(hex_string)
		return list_of_hex  
		
	return convert_to_hex(colorscale)

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


