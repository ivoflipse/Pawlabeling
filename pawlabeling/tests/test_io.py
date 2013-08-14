from unittest import TestCase
import os
import numpy as np
import shutil
import cPickle as pickle
from pawlabeling.functions import io
from pawlabeling.settings import configuration

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

    # Disabled this one, because its rather slow
    # def test_load_sample_zebris(self):
    #     """
    #     This test is a bit too long, perhaps I should get a smaller measurement.
    #     """
    #     parent_folder = os.path.dirname(os.path.abspath(__file__))
    #     file_location = "files\\zebris_export.zip"
    #     file_name = os.path.join(parent_folder, file_location)
    #     data = io.load(file_name=file_name)
    #     self.assertEqual(data.shape, (128L, 56L, 1472L))

class TestFindStoredFile(TestCase):
    def setUp(self):
        # Let's try and change the measurement folder
        root = os.path.dirname(os.path.abspath(__file__))
        file_name = os.path.join(root, "files\\empty_folder")
        # Cache the old location so we can reset it
        self.old_folder = configuration.store_results_folder
        # Change the configuration's folder
        configuration.store_results_folder = file_name

    def test_find_stored_file(self):
        io.find_stored_file(dog_name="Dog1", file_name="fake_export_1")

    def tearDown(self):
        # Restore it to the old folder
        configuration.store_results_folder = self.old_folder


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
        reversed_data = np.rot90(np.rot90(data))
        new_data = io.fix_orientation(data=reversed_data)
        # Check to see if its equal to the normal data again
        equal = np.array_equal(data, new_data)
        self.assertEqual(equal, True)

class TestLoadResults(TestCase):
    def test_load_successful(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\rsscan_export.zip.pkl"
        input_path = os.path.join(parent_folder, file_location)
        # This contains all the paws, check if they're all there
        results = io.load_results(input_path=input_path)
        # Perhaps I want to check more things here?
        self.assertEqual(len(results), 11)

    def test_load_failed(self):
        """
        If we supply an empty path or if the path is None, we get None back
        """
        results = io.load_results(input_path=None)
        self.assertEqual(results, None)

    def test_empty_results(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        # This file contains an empty dictionary
        file_location = "files\\fake_results.zip.pkl"
        input_path = os.path.join(parent_folder, file_location)
        # Loading this empty file should raise an exception
        with self.assertRaises(Exception):
            io.load_results(input_path=input_path)

    def test_empty_results_2(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        # This file contains json full of tweets
        file_location = "files\\fake_results_2.zip.pkl"
        input_path = os.path.join(parent_folder, file_location)
        # Loading this empty file should raise an exception
        with self.assertRaises(Exception):
            io.load_results(input_path=input_path)


class TestCreateResultsFolder(TestCase):
    def setUp(self):
        # Use some name hopefully nobody will ever use
        self.dog_name = "Professor Xavier Test"
        store_path = configuration.store_results_folder
        self.new_path = os.path.join(store_path, self.dog_name)

        if os.path.exists(self.new_path):
            #os.remove(self.new_path)
            # Using shutil instead of os, because of:
            # http://stackoverflow.com/questions/10861403/cant-delete-test-folder-in-windows-7
            shutil.rmtree(self.new_path, ignore_errors=True)

    def test_create_results_folder(self):
        exists = os.path.exists(self.new_path)
        self.assertFalse(exists)

        return_path = io.create_results_folder(self.dog_name)
        self.assertEqual(return_path, self.new_path)

        exists = os.path.exists(return_path)
        self.assertTrue(exists)

    def test_create_results_folder_with_empty_name(self):
        with self.assertRaises(Exception):
            io.create_results_folder(dog_name="")

    def tearDown(self):
        # Remove the folder we just created
        if os.path.exists(self.new_path):
            #os.remove(self.new_path)
            shutil.rmtree(self.new_path, ignore_errors=True)

class TestResultsToPickle(TestCase):
    def setUp(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        new_location = "files\\temp.zip"
        self.pickle_path_before = os.path.join(parent_folder, new_location)
        self.pickle_path_after = self.pickle_path_before + ".pkl"
        file_location = "files\\rsscan_export.zip.pkl"
        self.input_path = os.path.join(parent_folder, file_location)

        # Load paws from an existing pickle file
        with open(self.input_path, "rb") as pickle_file:
            self.paws = pickle.load(pickle_file)

        # Remove the folder if it exists
        if os.path.exists(self.pickle_path_after):
            shutil.rmtree(self.pickle_path_after, ignore_errors=True)

    def test_results_to_pickle(self):
        io.results_to_pickle(self.pickle_path_before, self.paws)

        exists = os.path.exists(self.pickle_path_after)
        self.assertTrue(exists)

    def test_results_to_pickle_wrong_path(self):
        with self.assertRaises(Exception):
            io.results_to_pickle(pickle_path="", paws=self.paws)

    def test_results_to_pickle_no_paws(self):
        with self.assertRaises(Exception):
            io.results_to_pickle(pickle_path=self.pickle_path_before, paws=[])

    def tearDown(self):
        # Remove the folder if it still exists
        if os.path.exists(self.pickle_path_after):
            shutil.rmtree(self.pickle_path_after, ignore_errors=True)


class TestZipFile(TestCase):
    def setUp(self):
        # Create a copy of an unzipped file
        self.root = os.path.dirname(os.path.abspath(__file__))
        file_location = "files\\fake_export"
        file_name = os.path.join(self.root, file_location)
        new_file_location = "files\\new_fake_export"
        self.new_file_name = os.path.join(self.root, new_file_location)
        # Create a copy of fake export
        shutil.copyfile(file_name, self.new_file_name)

    def test_zip_file(self):
        # Try zipping the file
        io.zip_file(self.root, self.new_file_name)

        # Check to see that the file exists
        exists = os.path.exists(self.new_file_name + ".zip")
        self.assertTrue(exists)

    def test_zip_file_wrong_root(self):
        with self.assertRaises(Exception):
            io.zip_file(root="", file_name=self.new_file_name)

    def test_zip_file_wrong_file_name(self):
        with self.assertRaises(Exception):
            io.zip_file(root=self.root, file_name="")

    def tearDown(self):
        # Remove the file if it still exists
        if os.path.exists(self.new_file_name + ".zip"):
            shutil.rmtree(self.new_file_name + ".zip", ignore_errors=True)


class TestGetFilePaths(TestCase):
    def setUp(self):
        # Let's try and change the measurement folder
        root = os.path.dirname(os.path.abspath(__file__))
        self.file_name = os.path.join(root, "files\\zip_folder")
        # Cache the old location so we can reset it
        self.old_folder = configuration.measurement_folder
        # Change the configuration's folder
        configuration.measurement_folder = self.file_name

        # If for some reason the folder doesn't exist, copy it over
        if not os.path.exists(self.file_name):
            # Copy files from zip_folder_copy
            shutil.copytree(self.file_name + "_copy", self.file_name)

    def test_get_file_paths(self):
        # Get the file_paths
        file_paths = io.get_file_paths()

        # Check if file_paths is correct
        self.assertEqual(sorted(file_paths.keys()), ["Dog1", "Dog2"])
        self.assertEqual(sorted(file_paths["Dog1"].keys()), ["fake_export_1.zip", "fake_export_2.zip", "fake_export_3.zip"])

    def tearDown(self):
        # Restore it to the old folder
        configuration.measurement_folder = self.old_folder
        # Delete the .zip  files
        shutil.rmtree(self.file_name)
        # Copy files from zip_folder_copy
        shutil.copytree(self.file_name + "_copy", self.file_name)


class TestGetFilePaths2(TestCase):
    """
    Second test case, but this time on an empty folder.
    This way I could reuse the setUp and tearDown.
    """
    def setUp(self):
        # Let's try and change the measurement folder
        root = os.path.dirname(os.path.abspath(__file__))
        file_name = os.path.join(root, "files\\empty_folder")
        # Cache the old location so we can reset it
        self.old_folder = configuration.measurement_folder
        # Change the configuration's folder
        configuration.measurement_folder = file_name

    def test_get_file_paths(self):
        with self.assertRaises(Exception):
            file_paths = io.get_file_paths()

    def tearDown(self):
        # Restore it to the old folder
        configuration.measurement_folder = self.old_folder