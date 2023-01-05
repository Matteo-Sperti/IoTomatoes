class CheckResult:
    def __init__(self, is_error: bool = False, message: str = "", device_id: int = None, measure_type: str = "", device_list: list = [], topic = ""):
        self.is_error = is_error
        self.message = message
        self.device_id = device_id
        self.measure_type = measure_type
        self.topic = topic