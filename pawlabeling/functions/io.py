import os
import logging

import numpy as np
from pubsub import pub


try:
    import cPickle as pickle
except ImportError:
    import pickle

logger = logging.getLogger("logger")


def calculate_distance(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))


def fix_orientation(data):
    from scipy.ndimage.measurements import center_of_mass
    # Find the first and last frame with nonzero measurement_data (from z)
    x, y, z = np.nonzero(data)
    # For some reason I was loading the file in such a way that it wasn't sorted
    z = sorted(z)
    start, end = z[0], z[-1]
    # Get the COP for those two frames
    start_x, start_y = center_of_mass(data[:, :, start])
    end_x, end_y = center_of_mass(data[:, :, end])
    # We've calculated the start and end point of the measurement (if at all)
    x_distance = end_x - start_x
    # If this distance is negative, the subject walked right to left
    #print .The distance between the start and end is: {}".format(x_distance)
    if x_distance < 0:
        # So we flip the measurement_data around
        data = np.rot90(np.rot90(data))
        #measurement_data = measurement_data[::-1,::-1,:]  #Alternative
    return data


def load_zebris(infile):
    """
    Input: raw text file, consisting of lines of strings
    Output: stacked numpy array (width x height x number of frames)

    This very crudely goes through the file, and if the line starts with an F splits it
    Then if the first word is Frame, it flips a boolean "frame_number"
    and parses every line until we hit the closing "}".
    """
    frame_number = None
    data_slices = []
    # Clean up the file
    split_input = [line for line in infile.split("\n") if len(line) > 0]

    for line in iter(split_input):
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

    # Check if we didn't pass an empty array
    if results.shape[2] == 1:
        raise Exception

    width, height, length = results.shape
    if width > height:
        return results
    else:
        return results.swapaxes(0, 1)


# TODO Check to replace the looping using iter with a sentinel value
# See Raymond Hettinger's presentation from PyCon about Beautiful Python
# This functions is modified from:
# http://stackoverflow.com/questions/4087919/how-can-i-improve-my-contact-detection
def load_rsscan(infile):
    """Reads all measurement_data in the datafile. Returns an array of times for each
    slice, and a 3D array of pressure measurement_data with shape (nx, ny, nz)."""
    from StringIO import StringIO

    width = 0
    height = 0
    frames = []

    lines = infile.splitlines()

    for index, line in enumerate(iter(lines)):
        split_line = line.strip().split()
        if split_line and split_line[-1] == "ms)":
            frames.append(index)

        # We'll count the number of lines in the first frame
        # and how long the first line is
        if split_line and not width and frames and index != frames[-1]:
            width = len(split_line)

    height = frames[1] - frames[0] - 2
    num_frames = len(frames)

    result = np.zeros((height, width, num_frames), dtype=np.float32)
    for frame, start in enumerate(frames):
        frame_string = StringIO("\n".join(lines[start+1:start+1+height]))
        result[:, :, frame] = np.loadtxt(frame_string, dtype=np.float32)  # unpack=True if we want to change the shape

    # Check if the array contains any NaN, if so, throw an Exception
    if np.isnan(result).any():
        logger.error("Measurements should never contain NaN. Please report this measurement file on Github.")
        raise Exception

    # Check if we didn't pass an empty array
    if result.shape[2] == 1:
        raise Exception
    return result

def load_tekscan(infile):
    """Reads all data in the datafile. Returns an array of times for each
    slice, and a 3D array of pressure data with shape (nx, ny, ntimes)."""
    data_slices = []
    data = []
    first_frame = False
    for line in iter(infile.splitlines()):
        split_line = line.strip().split(',')
        # Skip the whole header thing
        if split_line and split_line[0][:5] == "Frame":
            first_frame = True
            continue

        line_length = len(split_line)
        if first_frame:
            if line_length == 1:
                if data:
                    array_data = np.array(data, dtype=np.float32)
                    data_slices.append(array_data)
                    data = []
            else:
                data.append(split_line)

    result = np.dstack(data_slices)
    return result

def load(input_file, brand):
    if brand == "rsscan":
        try:
            return load_rsscan(input_file)
        except Exception as e:
            logger.debug("Loading with RSscan format failed. Exception: {}".format(e))
    elif brand == "zebris":
        try:
            return load_zebris(input_file)
        except Exception as e:
            logger.debug("Loading with Zebris format failed. Exception: {}".format(e))
    elif brand == "tekscan":
        try:
            return load_tekscan(input_file)
        except Exception as e:
            logger.debug("Loading with Tekscan format failed. Exception: {}".format(e))
    else:
        pub.sendMessage("update_statusbar", status="Couldn't load file")
        logger.warning("Couldn't load file. Please contact me for support.")


def open_zip_file(file_name):
    # Check if we even get a file_name
    if file_name == "":
        return None

    # Check if it ends with zip, else its probably a wrong file
    if file_name[-3:] != "zip":
        return None

    import zipfile

    # Load the zipped contents and pass them to the load functions
    infile = zipfile.ZipFile(file_name, "r")

    input_file = None  # Just in case the zip file is empty
    for file_name in infile.namelist():
        input_file = infile.read(file_name)

    return input_file


def zip_file(file_path):
    if not file_path:
        raise Exception("Incorrect file name")

    import zipfile

    # Create a new zip file and add .zip to the file_name
    new_file_path = file_path + ".zip"
    outfile = zipfile.ZipFile(new_file_path, "w")

    try:
        # Write the content from file_path to the zip-file called outfile
        outfile.write(file_path, os.path.basename(file_path), compress_type=zipfile.ZIP_DEFLATED)
    except Exception as e:
        logger.critical("Couldn't write to ZIP file. Exception: {}".format(e))
        # Raise another exception to let the caller deal with it
        raise Exception

    try:
        # Remove the uncompressed file
        os.remove(file_path)
    except Exception as e:
        logger.critical("Couldn't remove file original file. Exception: {}".format(e))
        # Raise another exception to let the caller deal with it
        raise Exception

    return new_file_path


def get_file_paths(measurement_folder):
    from collections import defaultdict

    # Clear any existing file names
    file_paths = defaultdict(list)

    logger.info("io.get_file_paths: Searching for measurements...")

    assert os.path.exists(measurement_folder)
    assert os.path.isdir(measurement_folder)
    file_names = [name for name in os.listdir(measurement_folder)]
    # Removed the isfile condition
    #if os.path.isfile(os.path.join(measurement_folder, name))

    for file_name in file_names:
        file_paths[file_name] = os.path.join(measurement_folder, file_name)

    if not file_paths:
        logger.info("No files found, please check the measurement folder in your settings file")
    return file_paths