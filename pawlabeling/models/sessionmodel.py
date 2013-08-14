import logging

logger = logging.getLogger("logger")

class SessionModel():
    def __init__(self):
        self.dog_name = ""
        self.measurements = []

    def switch_dogs(self, dog_name):
        """
        This function should always be called when you want to access other dog's results
        """
        if dog_name != self.dog_name:
            self.logger.info(
                "SessionModel.switch_dogs: Switching dogs from {} to {}".format(self.dog_name, dog_name))
            self.dog_name = dog_name

            # If switching dogs, we also want to clear our caches, because those values are useless
            self.clear_cached_values()

    def add_measurements(self, file_paths):
        self.measurements = file_paths[self.dog_name]

