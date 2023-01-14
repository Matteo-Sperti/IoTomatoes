class web_exception(Exception):
    def __init__(self, code, message):
        """Web exception class.
        
        ``code {int}``: error code and ``message {str}``: error message"""
        self.message = message
        self.code = code

class InfoException(Exception):
    def __init__(self, message):
        self.message = message

class CheckResult(Exception):
    def __init__(self, is_error: bool = False, message: str = "", device_id: int = -1, measure_type: str = "", device_list: list = [], topic = ""):
        self.is_error = is_error
        self.message = message
        self.device_id = device_id
        self.measure_type = measure_type
        self.topic = topic