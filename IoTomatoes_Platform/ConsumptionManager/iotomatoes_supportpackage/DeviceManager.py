def inList(deviceID: int, deviceList: list):
    """Check if an actuator is in the list of the actuators.

    Arguments:
    - `deviceID (int)`: ID of the device to check
    - `deviceList (list of dict)`: List of all devices
    
    Return: `CheckResult` object with:
    - `error (bool)`: ".is_error"
    - `message (str)`: ".message"
    """

    for dev in deviceList:
        if dev['ID'] == deviceID:
            return CheckResult(is_error=False)
    return CheckResult(is_error=True, messageType="Error", message="Device not found")


class CheckResult():
    def __init__(self, is_error: bool = False, messageType: str = "", message: str = "",
                 device_id: int = -1, measure_type: str = ""):
        self.is_error = is_error
        self.message = message
        self.messageType = messageType
        self.device_id = device_id
        self.measure_type = measure_type
