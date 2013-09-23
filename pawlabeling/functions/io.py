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


def check_orientation(data):
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
    return True if x_distance < 0 else False


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
    data_slices = []
    data = []
    for line in iter(infile.splitlines()):
        split_line = line.strip().split()
        line_length = len(split_line)
        if line_length == 0:
            if len(data) != 0:
                array_data = np.array(data, dtype=np.float32)
                data_slices.append(array_data)
        elif line_length == 4:  # header
            data = []
        else:
            data.append(split_line)

    # Because there won't be an empty line, I need to add the last frame outside the loop
    array_data = np.array(data, dtype=np.float32)
    data_slices.append(array_data)

    result = np.dstack(data_slices)
    # Check if we didn't pass an empty array
    if result.shape[2] == 1:
        raise Exception
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


def load_results(input_path):
    # Return if we don't have an input_path, this means there are no results
    if not input_path:
        return

    results = []
    with open(input_path, "rb") as pickle_file:
        results = pickle.load(pickle_file)

    # Empty results or non-list ones are not allowed
    if not results:
        raise Exception("Results are empty. Incorrect file or it could not be read")
    if type(results) is not list:
        raise Exception("Results are of the wrong type. You've used an incorrect file")

    # Check the type of the first item in the list
    from pawlabeling.models.contactmodel import Contact

    contacts = []
    for contact in results:
        contacts.append(isinstance(contact, Contact))
    if all(contacts):
        return results
    else:
        raise Exception("Results do not contain Contact's. You've used an incorrect file")


def results_to_pickle(pickle_path, contacts):
    """
    pickle_path is a path like "subject_name\\measurement_name"
    contacts is a list of Contacts

    It appends .pkl as an extensions to the pickle_path and
    uses pickle to dump the contacts to the file location
    """
    # Check if the parent folder exists
    parent_folder = os.path.dirname(pickle_path)
    if not os.path.exists(parent_folder):
        raise Exception("Parent folder does not exists, can't save the file")

    if not contacts:
        raise Exception("There are no contacts in this measurement, can't save the file")

    # Open a file with pkl (pickle) added to the path_name
    with open(pickle_path + ".pkl", "wb") as pickle_file:
        pickle.dump(contacts, pickle_file)


def zip_file(root, file_name):
    if not root:
        raise Exception("Incorrect root folder")

    if not file_name:
        raise Exception("Incorrect file name")

    import zipfile

    file_path = os.path.join(root, file_name)
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

    return os.path.join(root, new_file_path)


def get_file_paths():
    from collections import defaultdict
    from pawlabeling.settings import settings

    # Clear any existing file names
    file_paths = defaultdict(list)

    logger.info("io.get_file_paths: Searching for measurements...")

    root = settings.settings.measurement_folder()
    assert os.path.exists(root) == True
    assert os.path.isdir(root) == True
    file_names = [name for name in os.listdir(root)
                  if os.path.isfile(os.path.join(root, name))]

    for file_name in file_names:
        file_paths[file_name] = os.path.join(root, file_name)

    if not file_paths:
        logger.info("No files found, please check the measurement folder in your settings file")
    return file_paths