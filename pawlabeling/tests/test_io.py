import unittest
import os
from pawlabeling.functions import io


class TestLoad(unittest.TestCase):
    def load_sample_dog1(self):
        parent_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_location = "samples\\Measurements\\Dog1\\sel_1 - 3-4-2010 - Entire Plate Roll Off"
        file_name = os.path.join(parent_folder, file_location)
        print file_name
        data = io.load(file_name=file_name)
        print data.shape
        self.assertEqual(data.shape, ())


suite = unittest.TestLoader().loadTestsFromTestCase(TestLoad)
unittest.TextTestRunner(verbosity=2).run(suite)