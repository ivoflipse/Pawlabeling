from unittest import TestCase
import os
from pawlabeling.functions import io
import numpy as np

class TestLoad(TestCase):
    def test_load_sample_dog1(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        self.assertEqual(data.shape, (256L, 63L, 250L))

    def test_load_empty_file_name(self):
        data = io.load(file_name="")
        self.assertEqual(data, None)

    def test_load_non_zip_file(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip.pkl"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        self.assertEqual(data, None)

    def test_load_incorrect_file(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\fake_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        self.assertEqual(data, None)

    def test_load_sample_zebris(self):
        """
        This test is a bit too long, perhaps I should get a smaller measurement.
        """
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\zebris_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        self.assertEqual(data.shape, (128L, 56L, 1472L))

class TestFixOrientation(TestCase):
    def test_not_fixing(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        new_data = io.fix_orientation(data=data)
        equal = np.array_equal(data, new_data)
        self.assertEqual(equal, True)

    def test_fixing(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        # Reverse the plate around the longitudinal axis
        reversed_data = data[::-1,:,:]
        new_data = io.fix_orientation(data=reversed_data)
        # Check to see if its equal to the normal data again
        equal = np.array_equal(data, new_data)
        self.assertEqual(equal, True)