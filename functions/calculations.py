import numpy as np

def interpolate_time_series(data, length=100):
    from scipy import interpolate
    length_data = len(data)
    x = np.arange(0, length_data, 1)
    #xnew = np.linspace(0, len(data[:-1]), num=100)
    x_new = np.linspace(0, length_data-1, num=length)
    tck = interpolate.splrep(x, data)
    new_data = interpolate.splev(x_new, tck)
    return new_data

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




