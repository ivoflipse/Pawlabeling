from unittest import TestCase
import os
import numpy as np
from pawlabeling.functions import calculations, io

class TestCalculateCOP(TestCase):
    def test_calculate_cop_scipy(self):
        # How do I verify the COP is correct?
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)

        calculations.calculate_cop(data, version="scipy")


    # My version is slow as hell
    def test_calculate_cop_numpy(self):
        # How do I verify the COP is correct?
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)

        calculations.calculate_cop(data, version="numpy")


    def test_compare_cop(self):
        # Hurray both versions give the same results! Guess I did do something right then
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)

        cop_x1, cop_y1 = calculations.calculate_cop(data, version="numpy")
        cop_x2, cop_y2 = calculations.calculate_cop(data, version="scipy")

    def test_calculate_cop_dummy(self):
        # Create a dummy measurement
        data = np.zeros((3,3,3))
        data[1, 0, :] = 1

        cop_x, cop_y = calculations.calculate_cop(data, version="scipy")
        # print cop_x, cop_y
        # [ 0.  0.  0.] [ 1.  1.  1.]
        equal_x = np.array_equal(cop_x, np.array([0., 0., 0.]))
        equal_y = np.array_equal(cop_y, np.array([1., 1., 1.]))

        self.assertTrue(equal_x)
        self.assertTrue(equal_y)