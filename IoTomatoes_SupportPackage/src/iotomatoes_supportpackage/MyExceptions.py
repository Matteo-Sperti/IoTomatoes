class web_exception(Exception):
    def __init__(self, code, message):
        """Web exception class.

        Arguments:
        - `code (int)`: error code 
        - `message (str)`: error message"""
        self.message = message
        self.code = code


class InfoException(web_exception):
    def __init__(self, message):
        """Info exception class.

        Arguments:\n
        - `message (str)`: error message"""
        super().__init__(400, message)
