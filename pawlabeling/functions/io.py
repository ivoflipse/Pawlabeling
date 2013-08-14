import os
import logging
import numpy as np
from pubsub import pub
from pawlabeling.settings import configuration
try:
    import cPickle as pickle
except ImportError:
    import pickle

logger = logging.getLogger("logger")


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
        #data = data[::-1,::-1,:]  #Alternative
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


# This functions is modified from:
# http://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
def load_rsscan(infile):
    """Reads all data in the datafile. Returns an array of times for each
    slice, and a 3D array of pressure data with shape (nx, ny, nz)."""
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


def load(file_name):
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

    try:
        return load_rsscan(input_file)
    except Exception as e:
        logger.debug("Loading with RSscan format failed. Exception: {}".format(e))

    try:
        return load_zebris(input_file)
    except Exception as e:
        logger.debug("Loading with Zebris format failed. Exception: {}".format(e))

    pub.sendMessage("update_statusbar", status="Couldn't load file")
    logger.warning("Couldn't load file. Please contact me for support.")


def find_stored_file(dog_name, file_name):
    # Note that the file_name might have a ZIP extension, so we'll ignore that for now
    file_name = file_name.split(".")[0]
    root_folder = configuration.store_results_folder
    # For the current file_name, check if the results have been stored, if so load it
    path = os.path.join(root_folder, dog_name)
    # If the folder exists
    if os.path.exists(path):
        # Check if the current file's name is in that folder
        for root, dirs, files in os.walk(path):
            for f in files:
                name = f.split('.')[0]  # This was giving problems because of .zip.json == 2 extensions
                if name == file_name:
                    input_file = f
                    input_path = os.path.join(path, input_file)
                    return input_path


def load_results(input_path):
    # Throw an exception if the input_path is empty
    if not input_path:
        raise Exception("Empty input path")

    results = []
    if input_path:
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


def create_results_folder(dog_name):
    """
    This function takes a path and creates a folder called
    Returns the path of the folder just created
    """
    if not dog_name:
        raise Exception("You can't supply an empty name")

    store_path = configuration.store_results_folder
    # The name of the dog is the second last element in file_name
    new_path = os.path.join(store_path, dog_name)
    # Create a new folder in the base folder if it doesn't already exist
    if not os.path.exists(new_path):
        os.mkdir(new_path)
    return new_path


def results_to_pickle(pickle_path, paws):
    """
    pickle_path is a path like "dog_name\\measurement_name"
    paws is a list of Contacts

    It appends .pkl as an extensions to the pickle_path and
    uses pickle to dump the paws to the file location
    """
    # Check if the parent folder exists
    parent_folder = os.path.dirname(pickle_path)
    if not os.path.exists(parent_folder):
        raise Exception("Parent folder does not exists, can't save the file")

    if not paws:
        raise Exception("There are no contacts in this measurement, can't save the file")

    # Open a file with pkl (pickle) added to the path_name
    with open(pickle_path + ".pkl", "wb") as pickle_file:
        pickle.dump(paws, pickle_file)


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
    # Clear any existing file names
    file_paths = defaultdict(dict)

    logger.info("io.get_file_paths: Searching for measurements...")
    # Walk through the folder and gather up all the files
    for idx, (root, dirs, files) in enumerate(os.walk(configuration.measurement_folder)):
        if not dirs:
            # Add the name of the dog
            dog_name = root.split("\\")[-1]
            for index, file_name in enumerate(files):
                # zip_file will convert a file to zip and returns the path to the file
                if file_name[-3:] != "zip":
                    file_paths[dog_name][file_name] = zip_file(root, file_name)
                else:
                    file_paths[dog_name][file_name] = os.path.join(root, file_name)

    return file_paths