import threading
import time

class MyThread(threading.Thread):
    def __init__(self, target, args = None, interval = 1):
        super().__init__()
        self.target = target
        self.args = args
        self.interval = interval
        self.stop_event = threading.Event()
        self.daemon = True

    def stop(self):
        self.stop_event.set()

    def is_stopped(self):
        return self.stop_event.is_set()

    def run(self):
        while not self.is_stopped():
            self.target(*self.args)
            time.sleep(self.interval)