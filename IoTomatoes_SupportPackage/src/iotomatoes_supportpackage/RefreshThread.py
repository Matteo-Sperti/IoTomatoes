import time
import requests

from .MyThread import MyThread


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
