import threading
import time


class MyThread(threading.Thread):
    def __init__(self, target, interval: int = 1, *args, **kwargs):
        """MyThread class. Run a function in a daemon thread every interval seconds.

        - `target (function)`: function to be executed in the thread,
        - `args (tuple)`: arguments for the function
        - `interval (int)`: interval in seconds between executions"""

        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.interval = interval
        self.stop_event = threading.Event()
        self.daemon = True
        self.start()

    def stop(self):
        """Stop the thread if it's running."""

        self.stop_event.set()

    def is_stopped(self):
        """Return True if the thread has been stopped."""

        return self.stop_event.is_set()

    def run(self):
        """Run the thread."""

        while not self.is_stopped():
            self.target(*self.args, **self.kwargs)
            time.sleep(self.interval)


class SimpleThread(threading.Thread):
    def start(self):
        super(SimpleThread, self).start()
