import requests
import json
import time
import threading

class GenericService: 
    def __init__(self, Service_info : dict, ServiceCatalog_url : str) :
        self.ServiceCatalog_url = ServiceCatalog_url
        self.Service_info = Service_info
        self.ID = self.register(self.Service_info)
        
        t = threading.Thread(target=self.refresh)
        t.daemon = True
        t.start()

    def refresh(self) :
        refreshed = False
        while not refreshed:
            try:
                res = requests.put(self.ServiceCatalog_url + "refresh", params={"ID": self.ID})
                res.raise_for_status()
            except requests.exceptions.Timeout:
                 refreshed = False
            except requests.exceptions.HTTPError:
                 refreshed = False
            else:
                refreshed = True
        
        time.sleep(60)

    def register(self, Service_info : dict) :
        while True:
            try:
                res = requests.post(self.ServiceCatalog_url + "insert", json = Service_info)
                res.raise_for_status()
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as HTTPError:
                print(f"{HTTPError.response.status_code}: {HTTPError.response.title}\n")
            else:
                return res.json()["ID"]

if __name__ == "__main__":
    man = GenericService({}, "http://localhost:8080/ServiceCatalog/")
    while True:
        print("End of the program")