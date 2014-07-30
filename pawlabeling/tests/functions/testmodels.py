from unittest import TestCase
import os
import numpy as np
import logging
from ...settings import settings
from ...functions import io, calculations
from ...models import contactmodel, measurementmodel, platemodel

logger = logging.getLogger("logger")
logger.disabled = True


class TestContactTracking(TestCase):
    def setUp(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files/rsscan_verify_content.zip"
        file_name = os.path.join(parent_folder, file_location)
        input_file = io.open_zip_file(file_name)
        data = io.load(input_file, brand="rsscan")

        # We create a Mock measurement, so we don't have to go through everything
        self.measurement = measurementmodel.MockMeasurement(measurement_id="measurement_1",
                                                        data=data,
                                                        frequency=126)
        self.subject_id = "subject_1"
        self.session_id = "session_1"

        self.plate = platemodel.Plate()
        self.plate.sensor_width = 0.508
        self.plate.sensor_height = 0.762
        self.plate.sensor_surface = 0.387096

    def test_tracking_count(self):
        self.contact_model = contactmodel.MockContacts(subject_id=self.subject_id,
                                                        session_id=self.session_id,
                                                        measurement_id=self.measurement.measurement_id)
        self.contacts = self.contact_model.track_contacts(measurement=self.measurement,
                                                          measurement_data=self.measurement.data,
                                                          plate=self.plate, )
        self.assertEqual(len(self.contacts), 9)


class TestContactValidation(TestCase):
    def setUp(self):
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        file_location = "files/rsscan_verify_content.zip"
        file_name = os.path.join(parent_folder, file_location)
        input_file = io.open_zip_file(file_name)
        data = io.load(input_file, brand="rsscan")

        # We create a Mock measurement, so we don't have to go through everything
        self.measurement = measurementmodel.MockMeasurement(measurement_id="measurement_1",
                                                        data=data,
                                                        frequency=126)
        self.subject_id = "subject_1"
        self.session_id = "session_1"

        self.plate = platemodel.Plate()
        self.plate.sensor_width = 0.508
        self.plate.sensor_height = 0.762
        self.plate.sensor_surface = 0.387096

        self.contact_model = contactmodel.MockContacts(subject_id=self.subject_id,
                                                   session_id=self.session_id,
                                                   measurement_id=self.measurement.measurement_id)
        self.contacts = self.contact_model.track_contacts(measurement=self.measurement,
                                                          measurement_data=self.measurement.data,
                                                          plate=self.plate, )

    def test_edge_contact(self):
        edge_count = 0
        for contact in self.contacts:
            if contact.edge_contact:
                edge_count += 1

        self.assertEqual(edge_count, 1)

    def test_unfinished_contact(self):
        unfinished_count = 0
        for contact in self.contacts:
            if contact.unfinished_contact:
                unfinished_count += 1

        self.assertEqual(unfinished_count, 3)