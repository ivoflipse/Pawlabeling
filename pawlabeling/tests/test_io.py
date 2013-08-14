import unittest
import os
from pawlabeling.functions import io

class TestLoad(unittest.TestCase):
    def load_sample_dog1(self):
        parent_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_location = "samples\\Measurements\\Dog1\\sel_1 - 3-4-2010 - Entire Plate Roll Off"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        print data.shape
        self.assertEqual(data.shape, ())

    def load_non_existing_file(self):
        data = io.load(file_name="")
        self.assertEqual(data, None)

    def load_sample_zebris(self):
        parent_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_location = "samples\\Measurements\\Zebris\\Hund 2 - 20-04-2012 1_6.txt.zip"
        file_name = os.path.join(parent_folder, file_location)
        data = io.load(file_name=file_name)
        print data.shape
        self.assertEqual(data.shape, ())

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLoad)
    unittest.TextTestRunner(verbosity=2).run(suite)