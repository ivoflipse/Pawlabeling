import logging
from pubsub import pub
from pawlabeling.models import table
from pawlabeling.settings import settings

class PlateModel(object):
    def __init__(self):
        self.settings = settings.settings
        self.database_file = self.settings.database_file()
        self.plates_table = table.PlatesTable(database_file=self.database_file)

        plates = self.settings.setup_plates()
        # If not all plates are in the plates table, add them
        if len(self.plates_table.plates_table) != len(plates):
            for plate in plates:
                self.create_plate(plate)

        # Keep a dictionary with all the plates with their id as the key
        self.plates = {}
        for plate in self.plates_table.get_plates(plate={}):
            self.plates[plate["plate_id"]] = plate

    def create_plate(self, plate):
        """
        This function takes a plate dictionary object and stores it in PyTables
        """
        # Check if the plate is already in the table
        if self.plates_table.get_plate(brand=plate["brand"], model=plate["model"]).size:
            pub.sendMessage("update_statusbar", status="Model.create_plate: Plate already exists")
            return

        # Create a subject id
        plate_id = self.plates_table.get_new_id()
        plate["plate_id"] = plate_id

        self.plates_table.create_plate(**plate)
        pub.sendMessage("update_statusbar", status="Model.create_plate: Plate created")

    def get_plates(self, plate={}):
        plates = self.plates_table.get_plates(**plate)
        pub.sendMessage("update_plates", plates=plates)


    def put_plate(self, plate):
        self.plate = plate
        self.plate_id = plate["plate_id"]
        self.sensor_surface = self.plate["sensor_surface"]
        self.logger.info("Plate ID set to {}".format(self.plate_id))
        pub.sendMessage("update_plate", plate=self.plate)