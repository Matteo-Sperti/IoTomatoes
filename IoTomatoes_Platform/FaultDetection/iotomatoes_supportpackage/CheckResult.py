class CheckResult():
    """Class to return a result of a check."""

    def __init__(self, is_error: bool = False, messageType: str = "", message: str = "",
                 device_id: int = -1, measure_type: str = ""):
        """Constructor of the class.

        Arguments:
        - `is_error (bool)`: True if the check has found an error
        - `messageType (str)`: Type of the message
        - `message (str)`: Message to return
        - `device_id (int)`: ID of the device
        - `measure_type (str)`: Type of the measure
        """
        self.is_error = is_error
        self.message = message
        self.messageType = messageType
        self.device_id = device_id
        self.measure_type = measure_type
