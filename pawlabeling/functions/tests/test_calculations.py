from unittest import TestCase
import os
import numpy as np
import logging
from pawlabeling.functions import calculations, io
from pawlabeling.models import contactmodel

logger = logging.getLogger("logger")
logger.disabled = True


class TestCalculateCOP(TestCase):
    def setUp(self):
        self.contact = contactmodel.Contact(subject_id="subject_1",
                                            session_id="session_1",
                                            measurement_id="measurement_1")

    def test_calculate_cop_scipy(self):
        # How do I verify the COP is correct?
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files/rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        input_file = io.open_zip_file(file_name)
        self.contact.data = io.load(input_file, brand="rsscan")

        calculations.calculate_cop(self.contact, version="scipy")


    # My version is slow as hell
    def test_calculate_cop_numpy(self):
        # How do I verify the COP is correct?
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files/rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        input_file = io.open_zip_file(file_name)
        self.contact.data = io.load(input_file, brand="rsscan")

        calculations.calculate_cop(self.contact, version="numpy")


    def test_compare_cop(self):
        # Hurray both versions give the same results! Guess I did do something right then
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files/rsscan_export.zip"
        file_name = os.path.join(parent_folder, file_location)
        input_file = io.open_zip_file(file_name)
        self.contact.data = io.load(input_file, brand="rsscan")

        cop_x1, cop_y1 = calculations.calculate_cop(self.contact, version="numpy")
        cop_x2, cop_y2 = calculations.calculate_cop(self.contact, version="scipy")

        equal_x = np.array_equal(cop_x1, cop_x2)
        equal_y = np.array_equal(cop_y1, cop_y2)

        self.assertTrue(equal_x)
        self.assertTrue(equal_y)

    def test_calculate_cop_dummy(self):
        # Create a dummy measurement
        data = np.zeros((3, 3, 3))
        data[1, 0, :] = 1
        self.contact.data = data

        cop_x, cop_y = calculations.calculate_cop(self.contact, version="scipy")
        # print cop_x, cop_y
        # [ 0.  0.  0.] [ 1.  1.  1.]
        equal_x = np.array_equal(cop_x, np.array([0., 0., 0.]))
        equal_y = np.array_equal(cop_y, np.array([1., 1., 1.]))

        self.assertTrue(equal_x)
        self.assertTrue(equal_y)

    def test_calculate_cop_with_2d_array(self):
        self.contact.data = np.zeros((3, 3))
        with self.assertRaises(Exception):
            calculations.calculate_cop(self.contact)


class TestForceOverTime(TestCase):
    def setUp(self):
        self.contact = contactmodel.Contact(subject_id="subject_1",
                                            session_id="session_1",
                                            measurement_id="measurement_1")

    def test_force_over_time_naive_check(self):
        # Create an empty 3D array
        data = np.zeros((3, 3, 3))
        data[1, 1, 0] = 1.
        data[1, 1, 1] = 2.
        data[1, 1, 2] = 1.

        self.contact.data = data

        force_over_time = calculations.force_over_time(self.contact)

        self.assertEqual(len(force_over_time), 3)
        self.assertEqual(np.max(force_over_time), 2.)
        self.assertEqual(np.argmax(force_over_time), 1)

    def test_force_over_time_with_2d_array(self):
        self.contact.data = np.zeros((3, 3))
        with self.assertRaises(Exception):
            calculations.force_over_time(self.contact)


class TestPressureOverTime(TestCase):
    def setUp(self):
        self.contact = contactmodel.Contact(subject_id="subject_1",
                                            session_id="session_1",
                                            measurement_id="measurement_1")

    def test_pressure_over_time_naive_check(self):
        # Create an empty 3D array
        data = np.zeros((3, 3, 3))
        data[1, 1, 0] = 1.
        data[1, 1, 1] = 2.
        data[1, 1, 2] = 1.

        self.contact.data = data

        sensor_surface = 1.
        pressure_over_time = calculations.pressure_over_time(self.contact, sensor_surface=sensor_surface)

        self.assertEqual(len(pressure_over_time), 3)
        self.assertEqual(np.max(pressure_over_time), 2. / sensor_surface)
        self.assertEqual(np.argmax(pressure_over_time), 1)

    def test_pressure_over_time_with_2d_array(self):
        self.contact.data = np.zeros((3, 3))
        with self.assertRaises(Exception):
            calculations.pressure_over_time(self.contact)


class TestSurfaceOverTime(TestCase):
    def setUp(self):
        self.contact = contactmodel.Contact(subject_id="subject_1",
                                            session_id="session_1",
                                            measurement_id="measurement_1")

    def test_surface_over_time_naive_check(self):
        # Create an empty 3D array
        data = np.zeros((3, 3, 3))
        data[1, 1, 0] = 1.
        data[1, 1, 1] = 2.
        data[2, 1, 1] = 2.
        data[1, 1, 2] = 1.

        self.contact.data = data

        sensor_surface = 1.
        surface_over_time = calculations.surface_over_time(self.contact, sensor_surface=sensor_surface)

        self.assertEqual(len(surface_over_time), 3)
        self.assertEqual(np.max(surface_over_time), 2. * sensor_surface)
        self.assertEqual(np.argmax(surface_over_time), 1)

    def test_surface_over_time_with_2d_array(self):
        self.contact.data = np.zeros((3, 3))

        with self.assertRaises(Exception):
            calculations.surface_over_time(self.contact)


class TestPixelCountOverTime(TestCase):
    def setUp(self):
        self.contact = contactmodel.Contact(subject_id="subject_1",
                                            session_id="session_1",
                                            measurement_id="measurement_1")

    def test_pixel_count_over_time_naive_check(self):
        # Create an empty 3D array
        data = np.zeros((3, 3, 3))
        data[1, 1, 0] = 1.
        data[1, 1, 1] = 2.
        data[2, 1, 1] = 2.
        data[1, 1, 2] = 1.

        self.contact.data = data

        pixel_count_over_time = calculations.pixel_count_over_time(self.contact)

        self.assertEqual(len(pixel_count_over_time), 3)
        self.assertEqual(np.max(pixel_count_over_time), 2.)
        self.assertEqual(np.argmax(pixel_count_over_time), 1)

    def test_pixel_count_over_time_with_2d_array(self):
        self.contact.data = np.zeros((3, 3))
        with self.assertRaises(Exception):
            calculations.pixel_count_over_time(self.contact)


class TestInterpolateTimeSeries(TestCase):
    def test_interpolate_time_series_naive_check(self):
        data = np.arange(10)
        # Try the default length value
        new_data = calculations.interpolate_time_series(data)
        self.assertEqual(len(new_data), 100)

    def test_interpolate_time_series_shorter_length(self):
        data = np.arange(10)
        # Try a different value
        length = 20
        new_data = calculations.interpolate_time_series(data, length=length)
        self.assertEqual(len(new_data), length)

    def test_interpolate_time_series_with_2d_array(self):
        data = np.zeros((3, 3))
        with self.assertRaises(Exception):
            calculations.interpolate_time_series(data)