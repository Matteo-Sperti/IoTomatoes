class web_exception(Exception):
    def __init__(self, code, message):
        self.message = message
        self.code = code

class InfoException(Exception):
    def __init__(self, message):
        self.message = message