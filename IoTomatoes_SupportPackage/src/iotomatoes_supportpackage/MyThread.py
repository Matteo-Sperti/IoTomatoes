import threading
import requests
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


class RefreshThread(MyThread):
    def __init__(self, url: str, endpoint, interval=60, **kwargs):
        """RefreshThread class. Refresh the Catalog every `interval` seconds.

        - `url (str)`: Catalog URL.
        - `endpoint (object)`: Endpoint to be refreshed.
        - `interval (int)`: refresh interval in seconds (default = 60).
        """

        self._url = url
        self.endpoint = endpoint
        super().__init__(self.refresh_item, interval, **kwargs)

    def refresh_item(self):
        """Refresh item `ID` in the Catalog at `url`."""

        refreshed = False
        while not refreshed:
            try:
                param = {"ID": self.endpoint.ID}
                res = requests.put(self._url + "/refresh", params=param)
                res.raise_for_status()
                stat = res.json()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                if "Status" in stat:
                    if stat["Status"] == True:
                        refreshed = True
                        print(
                            f"Refreshed correctly to the Catalog; myID = {self.endpoint.ID}\n")
                    else:
                        # problem in the Catalog, maybe the item has been deleted
                        # register again
                        print(f"Error in the Catalog, trying to register again\n")
                        self.endpoint.restart()
                else:
                    print(stat)
                    time.sleep(1)
