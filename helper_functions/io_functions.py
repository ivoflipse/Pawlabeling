#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import json
import os
import numpy as np
from settings import configuration

def find_stored_file(dog_name, file_name):
    store_path = configuration.store_results_folder
    # For the current file_name, check if the results have been stored, if so load it
    path = os.path.join(store_path, dog_name)
    # If the folder exists
    if os.path.exists(path):
        # Check if the current file's name is in that folder
        for root, dirs, files in os.walk(path):
            for f in files:
                name, ext = f.split('.')
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
                for index, data in results[key].items():
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
