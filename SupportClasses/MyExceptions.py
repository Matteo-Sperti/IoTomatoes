class web_exception(Exception):
    def __init__(self, code, message):
        """Web exception class.
        
        ``code {int}``: error code and ``message {str}``: error message"""
        self.message = message
        self.code = code

class InfoException(Exception):
    def __init__(self, message):
        self.message = message