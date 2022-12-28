class web_exception(Exception):
    def __init__(self, code, message):
        self.message = message
        self.code = code