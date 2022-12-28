import requests
import json
import time
import threading

class GenericResource: 
    def __init__(self, Resource_info : dict, ServiceCatalog_url : str) :
        self.ServiceCatalog_url = ServiceCatalog_url
        self.Resource_info = Resource_info
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        self.ID = self.register(self.Resource_info)
        
        t = threading.Thread(target=self.refresh)
        t.daemon = True
        t.start()

    def refresh(self) :
        refreshed = False
        while not refreshed:
            try:
                res = requests.put(self.ResourceCatalog_url + "refresh", params={"ID": self.ID})
                res.raise_for_status()
            except requests.exceptions.Timeout:
                 refreshed = False
            except requests.exceptions.HTTPError:
                 refreshed = False
            else:
                refreshed = True
        
        time.sleep(60)

    def get_ResourceCatalog_url(self) :
        while True:
            try:
                res = requests.get(self.ResourceCatalog_url + "search/serviceName", params = {"serviceName": "ResourceCatalog"})
                res.raise_for_status()
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as HTTPError:
                print(f"{HTTPError.response.status_code}: {HTTPError.response.title}\n")
            else:
                try:
                    for services in res.json()["servicesDetails"]:
                        if services["serviceType"] == "REST":
                            return services["serviceIP"]
                except KeyError:
                    print(f"Error in the Resource information\nRetrying connection\n")
        
    def register(self, Resource_info : dict) :
        while True:
            try:
                res = requests.post(self.ResourceCatalog_url + "insert", json = Resource_info)
                res.raise_for_status()
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as HTTPError:
                print(f"{HTTPError.response.status_code}: {HTTPError.response.title}\n")
            else:
                return res.json()["ID"]

if __name__ == "__main__":
    man = GenericResource({}, "http://localhost:8080/ServiceCatalog/")
    while True:
        print("End of the program")