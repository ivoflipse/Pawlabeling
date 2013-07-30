import json
import os
import logging
import numpy as np
from functions.pubsub import pub
from settings import configuration

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
    width, height, length = results.shape
    return results if width > height else results.swapaxes(0, 1)

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
        elif line_length == 4: # header
            data = []
        else:
            data.append(split_line)
    result = np.dstack(data_slices)
    return result

def load(file_name):
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

def reconstruct_data(shape, rows, columns, frames, values):
    data = np.zeros(shape)
    for row, column, frame, value in zip(rows, columns, frames, values):
        data[row, column, frame] = float(value)
    return data

def load_results(dog_name, measurement_name):
    input_path = find_stored_file(dog_name, measurement_name)
    results = {}
    # If an inputFile has been found, unpickle it
    if input_path:
        json_string = ""
        with open(input_path, "r") as json_file:
            for line in json_file:
                json_string += line
        results = json.loads(json_string)
        # Make sure all the keys are not unicode
        for key, value in results.items():
            if type(value) == dict:
                for index, data in value.items():
                    results[key][int(index)] = data
                    del results[key][index]  # Delete the unicode key

        for index, paw_data in results["paw_data"].items():
            data_shape, rows, cols, frames, values = paw_data
            data = reconstruct_data(data_shape, rows, cols, frames, values)
            # Overwrite the results with the restored version
            results["paw_data"][int(index)] = data
    return results

def create_results_folder(dog_name):
    """
    This function takes a path and creates a folder called
    Returns the path of the folder just created
    """
    store_path = configuration.store_results_folder
    # The name of the dog is the second last element in file_name
    new_path = os.path.join(store_path, dog_name)
    # Create a new folder in the base folder if it doesn't already exist
    if not os.path.exists(new_path):
        os.mkdir(new_path)
    return new_path

def results_to_json(new_path, dog_name, measurement_name, paw_labels, paws, paw_data):
    """
    This creates a json file for the current measurement and stores the results
    """
    json_file_name = "{}//{}.json".format(new_path, measurement_name)
    with open(json_file_name, "w+") as json_file:
        # Update somewhere in between
        results = {"dog_name": dog_name,
                   "measurement_name": measurement_name,
                   "paw_labels": paw_labels[measurement_name],
                   "paw_results": [paw.contact_to_dict() for paw in paws[measurement_name]],
                   "paw_data": {}
        }

        for index, data in enumerate(paw_data[measurement_name]):
            values = []
            rows, columns, frames = np.nonzero(data)
            for row, column, frame in zip(rows, columns, frames):
                values.append("{:10.4f}".format(data[row, column, frame]))
            results["paw_data"][index] = [data.shape, rows.tolist(), columns.tolist(), frames.tolist(), values]

        json_file.seek(0)  # Rewind the file, so we overwrite it
        json_file.write(json.dumps(results))
        json_file.truncate()  # In case the new file is smaller

def convert_file_to_zip(file_path):
    import zipfile
    # Create a new zip file and add .zip to the file_name
    new_file_path = file_path + ".zip"
    outfile = zipfile.ZipFile(new_file_path, "w")
    try:
        outfile.write(file_path, os.path.basename(file_path), compress_type=zipfile.ZIP_DEFLATED)
    except Exception as e:
        logger.critical("Couldn't write to ZIP file. Exception: {}".format(e))
    try:
        # Remove the uncompressed file
        os.remove(file_path)  # Its possible that this file is open somewhere else, then everything might fail...
        return new_file_path
    except Exception as e:
        logger.critical("Couldn't remove file original file. Exception: {}".format(e))

def zip_files(root, file_name):
    # Check if the file isn't compressed, else zip it and delete the original after loading
    base_name, extension = os.path.splitext(file_name)
    if extension != ".zip":
        file_path = os.path.join(root, file_name)
        file_name = convert_file_to_zip(file_path)

    return os.path.join(root, file_name)

def load_file_paths():
    from collections import defaultdict
    # Clear any existing file names
    file_paths = defaultdict(dict)

    logger.info("io.load_file_paths: Searching for measurements...")
    # Walk through the folder and gather up all the files
    for idx, (root, dirs, files) in enumerate(os.walk(configuration.measurement_folder)):
        if not dirs:
            # Add the name of the dog
            dog_name = root.split("\\")[-1]
            for index, file_name in enumerate(files):
                # zip_files will convert a file to zip and returns the path to the file
                file_paths[dog_name][file_name] = zip_files(root, file_name)

    return file_paths

