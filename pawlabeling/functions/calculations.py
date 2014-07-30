from collections import defaultdict
import numpy as np
from ..settings import settings

class MockMeasurement(object):
    def __init__(self, measurement_id, data, frequency):
        self.measurement_id = measurement_id
        self.data = data
        x, y, z = data.shape
        self.number_of_rows = x
        self.number_of_columns = y
        self.number_of_frames = z
        self.orientation = True
        self.frequency = frequency

class MockContact(object):
    def __init__(self, contact_id, data):
        self.contact_id = contact_id
        self.data = data


def asymmetry_index(left, right, absolute=False):
    """
    This function offers two versions, where the difference is in the numerator.
    When absolute is True, the function will return the size of the difference between left and right
    regardless of the direction of the difference.
    The following equation is used:
    (|XR - XL|/ |XR + XL| X 0.5) X 100
    where XR is the mean of a given gait variable for right footfalls
    during a 10-second recording and XL is the mean of a given gait variable
    for left footfalls during a 10-second recording
    See Oosterlinck et al. as a references.
    """
    # This function only accepts ints and floats
    assert isinstance(left, int) or isinstance(left, float)
    assert isinstance(right, int) or isinstance(right, float)

    if absolute:
        return (100. * abs(left - right)) / (0.5 * abs(left + right))
    else:
        return (100. * (left - right)) / (0.5 * abs(left + right))


def interpolate_time_series(data, length=100):
    """
    Interpolate time series expects a 1D array
    It will interpolate it to the defined length or use 100 as a default
    """
    assert len(data.shape) == 1
    from scipy import interpolate

    x = np.arange(0, len(data))
    f = interpolate.interp1d(x, data, bounds_error=False)
    x_new = np.linspace(0, len(data) - 1, num=length)
    data_new = f(x_new)
    return data_new


def calculate_cop(contact, version="scipy"):
    assert len(contact.data.shape) == 3
    if version == "scipy":
        contact.cop_x, contact.cop_y = calculate_cop_scipy(contact)
    elif version == "numpy":
        contact.cop_x, contact.cop_y = calculate_cop_numpy(contact)
    return contact.cop_x, contact.cop_y

def calculate_cop_numpy(contact):
    y, x, z = np.shape(contact.data)
    cop_x = np.zeros(z, dtype=np.float32)
    cop_y = np.zeros(z, dtype=np.float32)

    x_coordinate, y_coordinate = np.arange(x), np.arange(y)
    temp_x, temp_y = np.zeros(y), np.zeros(x)
    for frame in xrange(z):
        if np.sum(contact.data[:, :, frame]) > 0.0:  # Else divide by zero
            # This can be rewritten as a vector calculation
            for col in xrange(y):
                temp_x[col] = np.sum(contact.data[col, :, frame] * x_coordinate)
            for row in xrange(x):
                temp_y[row] = np.sum(contact.data[:, row, frame] * y_coordinate)
            # np.divide should guard against divide by zero
            cop_x[frame] = np.divide(np.sum(temp_x), np.sum(contact.data[:, :, frame]))
            cop_y[frame] = np.divide(np.sum(temp_y), np.sum(contact.data[:, :, frame]))
    return cop_x, cop_y

def calculate_cop_scipy(contact):
    from scipy.ndimage.measurements import center_of_mass

    y, x, z = np.shape(contact.data)
    cop_x = np.zeros(z, dtype=np.float32)
    cop_y = np.zeros(z, dtype=np.float32)
    for frame in xrange(z):
        if np.sum(contact.data[:, :, frame]) > 0:
            # While it may seem odd, x and y are mixed up, must be my own fault
            y, x = center_of_mass(contact.data[:, :, frame])
            # This used to say + 1, but I can't image that's necessary
            cop_x[frame] = x
            cop_y[frame] = y
    return cop_x, cop_y

# Given the size of the movement, it makes more sense to put this in mm/ms instead of ms/s
def velocity_of_cop(contact, sensor_width, sensor_height, frequency):
    # contact_duration = stance_duration(contact, frequency)
    cop_x = contact.cop_x
    cop_y = contact.cop_y
    step_size = 1000. / frequency
    distances = []
    distances_x = []
    distances_y = []
    diagonal_distance = np.sqrt(sensor_width ** 2 + sensor_height ** 2)
    for i in range(2, len(cop_x)):
        x1 = cop_x[i - 1]
        x2 = cop_x[i]
        y1 = cop_y[i - 1]
        y2 = cop_y[i]
        dx = x2 - x1
        dy = y2 - y1
        dxy = dx + dy
        # Convert to mm
        dx *= sensor_width
        dy *= sensor_height
        dxy *= diagonal_distance
        # Convert to mm/s
        dx *= step_size
        dy *= step_size
        dxy *= step_size
        distances.append(dxy)
        distances_x.append(dx)
        distances_y.append(dy)
    return distances, distances_x, distances_y

def force_over_time(contact):
    """
    Force over time calculates the total force for each frame.
    It expects the last dimension to always be frames,
    while the other two dimensions are the rows and columns
    """
    assert len(contact.data.shape) == 3
    contact.force_over_time = np.sum(np.sum(contact.data, axis=0), axis=0)
    return contact.force_over_time


def pixel_count_over_time(contact):
    assert len(contact.data.shape) == 3
    #x, y , z = np.transpose(np.count_nonzero(contact.data))
    #contact.pixel_counts = z
    #return contact.pixel_counts
    x, y, z = contact.data.shape
    contact.pixel_count_over_time = np.array([np.count_nonzero(contact.data[:, :, frame]) for frame in xrange(z)])
    return contact.pixel_count_over_time


def surface_over_time(contact, sensor_surface):
    assert len(contact.data.shape) == 3
    if not hasattr(contact, "pixel_count_over_time"):
        pixel_count_over_time(contact)

    contact.surface_over_time = np.dot(contact.pixel_count_over_time, sensor_surface)
    return contact.surface_over_time


def pressure_over_time(contact, sensor_surface):
    assert len(contact.data.shape) == 3
    if not hasattr(contact, "force_over_time"):
        force_over_time(contact)
    if not hasattr(contact, "surface_over_time"):
        surface_over_time(contact, sensor_surface)

    contact.pressure_over_time = np.divide(contact.force_over_time, contact.surface_over_time)
    return contact.pressure_over_time

def max_force(contact):
    if hasattr(contact, "force_over_time"):
        force_over_time(contact)
    return np.max(contact.force_over_time)

def max_pressure(contact, sensor_surface):
    if hasattr(contact, "pressure_over_time"):
        pressure_over_time(contact)
    return np.max(contact.pressure_over_time)

def max_surface(contact, sensor_surface):
    if hasattr(contact, "surface_over_time"):
        surface_over_time(contact, sensor_surface)
    return np.max(contact.surface_over_time)

def time_of_peak_force(contact, frequency, relative=True):
    """
    Simply the argmax of the maximum value (assuming there is only one...).
    I can either calculate this on the average or calculate this for each contact and then take an average over those values.
    Though this should use the frequency of the measurement to express it in milliseconds.
    """
    location_peak = max_force(contact)
    duration = contact.length
    if relative:
        contact.time_of_peak_force = (100. * location_peak) / duration
    else:
        contact.time_of_peak_force = (location_peak * 1000) / frequency
    return contact.time_of_peak_force


def vertical_impulse_method1(contact, frequency, mass):
    """
    From Oosterlinck:
    Vertical impulse (VI) was calculated by time integration of the force-time curves and multiplied by time,
    normalised by weight and expressed as Newton-seconds per kilogram (N s/kg)
    So wouldn't that just be one value? Namely the surface under the entire force curve?
    """
    # Normalize the force over time by mass
    force_over_time = np.divide(contact.force_over_time, mass * frequency)
    sum_force = np.sum(force_over_time)
    return sum_force

# If you integrate with step size 1, you basically take the sum
# You can use simps, but the difference is like 0.01-0.05 N*s
def vertical_impulse_trapz(contact, frequency, mass=1.0):
    """
    From Oosterlinck:
    Vertical impulse (VI) was calculated by time integration of the  force-time curves and multiplied by time,
    normalised by weight and expressed as Newton-seconds per kilogram (N s/kg)
    So wouldn't that just be one value? Namely the surface under the entire force curve?
    """
    from scipy.integrate import trapz  # simps is an alternative

    force_over_time = np.divide(contact.force_over_time, mass)
    sum_force = trapz(force_over_time, dx=1 / frequency)
    return sum_force


def vertical_impulse(contact, frequency, mass=1.0, version="1"):
    """
    Careful, I would recommend using mass in Newtons instead of kilograms
    """
    if version == "1":
        return vertical_impulse_method1(contact, frequency, mass)
    elif version == "2":
        return vertical_impulse_trapz(contact, frequency, mass)

##########################################################################################
# Spatiotemporal functions
def temporal_spatial(contacts, measurement_data, sensor_width, sensor_height, frequency):
    distances = defaultdict()
    label_lookup = defaultdict(dict)
    direction_modifier = 1.
    if detect_direction(measurement_data):
        direction_modifier = -1.
    for index, contact in enumerate(contacts):
        lookup_table = defaultdict(int)
        distance = defaultdict()
        for index2 in range(1, 5):
            new_index = index + index2
            # Don't bother if we're near the end
            if new_index >= len(contacts):
                continue

            other_contact = contacts[new_index]
            other_label = other_contact["contact_label"]
            # If we hit a contact for the second time
            if other_label in lookup_table:
                break

            label_lookup[index][other_label] = new_index

            # Lets skip bad contacts mkay?
            lookup_table[other_label] = 1
            if other_contact["invalid"] or other_contact["filtered"] or other_contact["contact_label"] < 0:
                continue

            x_dist = ((other_contact["min_x"] + ((other_contact["min_x"] - other_contact["max_x"]) / 2.)) -
                      (contact["min_x"] + ((contact["min_x"] - contact["max_x"]) / 2.)))
            y_dist = ((other_contact["min_y"] + ((other_contact["min_y"] - other_contact["max_y"]) / 2.)) -
                      (contact["min_y"] + ((contact["min_y"] - contact["max_y"]) / 2.)))
            z_dist = other_contact["min_z"] - contact["min_z"]

            # Flip directions is the measurement is the other way around
            x_dist *= sensor_height * direction_modifier
            y_dist *= sensor_width * direction_modifier
            z_dist = (1000 * z_dist) / frequency

            distance[other_label] = (x_dist, y_dist, z_dist)

        distances[index] = distance
    return distances, label_lookup


def gait_velocity(contacts, sensor_width, sensor_height, frequency):
    """
    Calculate the velocity of the gait by dividing the average stride length
    by the average swing time.

    Can't this be calculated from taking steps between front paws for example?
    """
    sensor_width = 1.
    sensor_height = 1.
    frequency = 100.
    distances = temporal_spatial(contacts, sensor_width, sensor_height, frequency)
    step_lookup = {0: 2, 1: 3, 2: 0, 3: 1}
    speed = []
    contact_labels = {}
    for index, contact in enumerate(contacts):
        contact_labels[index] = contact["contact_label"]

    step_size = 1. / frequency
    # Loop through distances and check if we find the same contact in
    # the embedded distance dictionary
    for contact_id, distance in distances.items():
        contact_label_1 = contact_labels[contact_id]
        if contact_label_1 < 0:
            continue
        for contact_label_2, (x, y, z) in distance.items():
            if contact_label_1 == contact_label_2:
                if not z:
                    continue
                # The * 1000 is to turn it into meters/second
                new_x = x * 1000.
                new_z = z * 1000.
                speed.append(new_x / new_z)
            if contact_label_2 == step_lookup[contact_label_1]:
                # How could this not be there? Because of defaultdict?
                if not z:
                    continue
                # The * 1000 is to turn it into meters/second
                new_x = x * 1000.
                new_z = z * 1000.
                speed.append(new_x / new_z)

    return speed


# I seem to have multiple versions of this code
# def gait_velocity(contacts, sensor_width=sensor_width, sensor_height=sensor_height, frequency=frequency):
# """
#     Calculate the velocity of the gait by dividing the average stride length
#     by the average swing time.
#
#     Can't this be calculated from taking steps between front paws for example?
#     """
#     distances = temporal_spatial(contacts)
#     step_lookup = {0: 2, 1: 3, 2: 0, 3: 1}
#     speed = []
#     contact_labels = {}
#     for index, contact in enumerate(contacts):
#         contact_labels[index] = contact["contact_label"]
#
#     step_size = 1. / frequency
#     for contact_id, distance in distances.items():
#         contact_label_1 = contact_labels[contact_id]
#         if contact_label_1 not in [0,2]:
#             continue
#         if contact_label_1 in distance:
#             x, y, z = distance[contact_label_1]
#             speed.append(x / (z+1))  # So we don't divide by zero
#         if step_lookup[contact_label_1] in distance:
#             x, y, z = distance[step_lookup[contact_label_1]]
#             speed.append(x / (z+1))  # So we don't divide by zero
#
#     return speed

def stance_duration(contact, frequency):
    """
    Calculates the total time the contact makes contact with the plate
    Returns the contact duration in ms
    """
    duration = contact["data"].read().shape[2]
    return (duration * 1000) / frequency


# I can't demo this now, because I don't have labeled contacts...
def swing_duration(contact_1, contact_2, frequency):
    """
    Calculate the time between two contacts of the same paw.
    This is calculated by taking the difference between the last frame
    of contact_1 and the first frame of contact_2 and converting it to ms
    """
    # assert that the contacts are from the same measurement
    assert contact_1["contact_label"] == contact_2["contact_label"]
    # If contact_2 occurs before contact_1, switch them around.
    if contact_1["min_z"] > contact_2["min_z"]:
        contact_1, contact_2 = contact_2, contact_1
    toe_off = contact_1["max_z"]
    heel_strike = contact_2["min_z"]
    difference = heel_strike - toe_off
    return (difference * 1000) / frequency


def step_duration(contact_1, contact_2, frequency):
    difference = abs(contact_1["min_z"] - contact_2["min_z"])
    return (difference * 1000) / frequency






def get_percentile(data, percent=5):
    cut_off = percent / 2.
    low = np.percentile(data, cut_off)
    high = np.percentile(data, 100 - cut_off)
    return [x for x in data if x > low and x < high]


def find_gait_pattern(pattern):
    stride_patterns = {'0-2-1-3': ['0-2-1-3',
                                   '0-2-1',
                                   '2-1-3-0',
                                   '2-1-3',
                                   '1-3-0-2',
                                   '1-3-0',
                                   '3-0-2-1',
                                   '3-0-2'],
                       '0-2-3-1': ['0-2-3-1',
                                   '0-2-3',
                                   '2-3-1-0',
                                   '2-3-1',
                                   '3-1-0-2',
                                   '3-1-0',
                                   '1-0-2-3',
                                   '1-0-2'],
                       '0-3-2-1': ['0-3-2-1',
                                   '0-3-2',
                                   '3-2-1-0',
                                   '3-2-1',
                                   '2-1-0-3',
                                   '2-1-0',
                                   '1-0-3-2',
                                   '1-0-3'],
                       '2-0-1-3': ['2-0-1-3',
                                   '2-0-1',
                                   '0-1-3-2',
                                   '0-1-3',
                                   '1-3-2-0',
                                   '1-3-2',
                                   '3-2-0-1',
                                   '3-2-0'],
                       '2-0-3-1': ['2-0-3-1',
                                   '2-0-3',
                                   '0-3-1-2',
                                   '0-3-1',
                                   '3-1-2-0',
                                   '3-1-2',
                                   '1-2-0-3',
                                   '1-2-0'],
                       '2-3-0-1': ['2-3-0-1',
                                   '2-3-0',
                                   '3-0-1-2',
                                   '3-0-1',
                                   '0-1-2-3',
                                   '0-1-2',
                                   '1-2-3-0',
                                   '1-2-3']}
    matches = []
    for i in range(len(pattern) - 4):
        if pattern[i] != "-":
            for j in [5, 7]:
                pat = pattern[i:i + j]
                for key, values in stride_patterns.items():
                    if pat in values:
                        matches.append(key)

    if not matches:
        return None
    elif len(set(matches)) == 1:
        return matches[0]
    else:
        most_common = None
        most_count = 0
        for match in set(matches):
            c = matches.count(match)
            if c > most_count:
                most_count = c
                most_common = match

        return most_common


#######################################################################################
# Validation functions
#######################################################################################

def check_valid(contact_list, weight):
    contact_order = [contact["contact_label"] for contact in contact_list]
    pattern = "-".join([str(contact["contact_label"]) for contact in contact_list])
    pattern = find_gait_pattern(pattern)

    speed = gait_velocity(contact_list)[1:-1]
    distances = temporal_spatial(contact_list)
    widths = []
    for index, distance in distances.items():
        cl = contact_order[index]
        if cl < 0:
            continue
        if cl in distance:
            x, y, z = distance[cl]
            widths.append(abs(y) / weight)

    contact_order = [contact["contact_label"] for contact in contact_list if
                     not contact["filtered"] and not contact["invalid"] and not contact["contact_label"] < 0]
    all_paws = set(contact_order) == {0, 1, 2, 3}
    no_acceleration = np.std(speed) < 0.2
    right_pattern = pattern in ['2-3-0-1', '0-3-2-1']
    straight_line = np.mean(widths) < 10

    return all_paws and no_acceleration and right_pattern and straight_line


def check_orientation(measurement_data):
    from scipy.ndimage.measurements import center_of_mass
    # Find the first and last frame with nonzero measurement_data (from z)
    x, y, z = np.nonzero(measurement_data)
    # For some reason I was loading the file in such a way that it wasn't sorted
    z = sorted(z)
    start, end = z[0], z[-1]
    # Get the COP for those two frames
    start_x, start_y = center_of_mass(measurement_data[:, :, start])
    end_x, end_y = center_of_mass(measurement_data[:, :, end])
    # We've calculated the start and end point of the measurement (if at all)
    x_distance = end_x - start_x
    # If this distance is negative, the subject walked right to left
    return True if x_distance < 0 else False