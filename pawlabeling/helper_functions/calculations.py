#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np

def calculate_cop(data, version="scipy"):
    if version == "scipy":
        return calculate_cop_scipy(data)
    else:
        return calculate_cop_manually(data)

def calculate_cop_manually(data):
    cop_x, cop_y = [], []
    y, x, z = np.shape(data)
    x_coordinate, y_coordinate = np.arange(1, x + 1), np.arange(1, y + 1)
    temp_x, temp_y = np.zeros((y, z)), np.zeros((x, z))
    for frame in range(z):
        if np.sum(data[:, :, frame]) != 0.0: # Else divide by zero
            for col in range(y):
                temp_x[col, frame] = np.sum(data[col, :, frame] * x_coordinate)
            for row in range(x):
                temp_y[row, frame] = np.sum(data[:, row, frame] * y_coordinate)
            if np.sum(temp_x[:, frame]) != 0.0 and np.sum(temp_y[:, frame]) != 0.0:
                cop_x.append(np.round(np.sum(temp_x[:, frame]) / np.sum(data[:, :, frame]), 2))
                cop_y.append(np.round(np.sum(temp_y[:, frame]) / np.sum(data[:, :, frame]), 2))
    return cop_x, cop_y

def calculate_cop_scipy(data):
    from scipy.ndimage.measurements import center_of_mass
    cop_x, cop_y = [], []
    height, width, length = data.shape
    for frame in range(length):
        y, x = center_of_mass(data[:, :, frame])
        cop_x.append(x + 1)
        cop_y.append(y + 1)
    return cop_x, cop_y




