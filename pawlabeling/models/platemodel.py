import logging
from ..models import table
from ..settings import settings


class Plates(object):
    def __init__(self):
        self.table = settings.settings.table
        self.plates_table = table.PlatesTable(table=self.table)

    def get_plates(self):
        # Keep a dictionary with all the plates with their id as the key
        self.plates = {}
        for plate in self.plates_table.get_plates():
            plate_object = Plate()
            plate_object.restore(plate=plate)
            self.plates[plate_object.plate_id] = plate_object
        return self.plates

    def create_plates(self):
        for plate in settings.settings.setup_plates():
            self.create_plate(plate)

    def create_plate(self, plate):
        """
        This function takes a plate dictionary object and stores it in PyTables
        """
        plate_object = Plate()
        # Check if the plate is already in the table
        if self.plates_table.get_plate(brand=plate["brand"], model=plate["model"]):
            return

        # Create a subject id
        plate_id = self.plates_table.get_new_id()
        plate_object.create_plate(plate_id=plate_id, plate=plate)
        plate = plate_object.to_dict()
        self.plates_table.create_plate(**plate)
        return plate_object

    # I'm not sure I want to put such information
    def put_plate(self, plate):
        self.plate = plate


class Plate(object):
    """
        plate_id = tables.StringCol(64)
        brand = tables.StringCol(32)
        model = tables.StringCol(32)
        number_of_rows = tables.Int16Col()
        number_of_columns = tables.Int16Col()
        sensor_width = tables.FloatCol()
        sensor_height = tables.FloatCol()
        sensor_surface = tables.FloatCol()
    """

    def __init__(self):
        pass

    def create_plate(self, plate_id, plate):
        self.plate_id = plate_id
        self.brand = plate["brand"]
        self.model = plate["model"]
        self.number_of_rows = plate["number_of_rows"]
        self.number_of_columns = plate["number_of_columns"]
        self.sensor_width = plate["sensor_width"]
        self.sensor_height = plate["sensor_height"]
        self.sensor_surface = plate["sensor_surface"]

    def to_dict(self):
        plate = {
            "plate_id": self.plate_id,
            "brand": self.brand,
            "model": self.model,
            "number_of_rows": self.number_of_rows,
            "number_of_columns": self.number_of_columns,
            "sensor_width": self.sensor_width,
            "sensor_height": self.sensor_height,
            "sensor_surface": self.sensor_surface,
        }
        return plate

    def restore(self, plate):
        self.plate_id = plate["plate_id"]
        self.brand = plate["brand"]
        self.model = plate["model"]
        self.number_of_rows = plate["number_of_rows"]
        self.number_of_columns = plate["number_of_columns"]
        self.sensor_width = plate["sensor_width"]
        self.sensor_height = plate["sensor_height"]
        self.sensor_surface = plate["sensor_surface"]