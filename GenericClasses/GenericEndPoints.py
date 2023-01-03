import requests
import time
import threading
from MyMQTT import MyMQTT
from ItemInfo import ServiceInfo
from customExceptions import InfoException

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

class RefreshThread(MyThread):
    def __init__(self, url : str, ID : int, interval=60):
        super().__init__(self.refresh_item, (url, ID), interval)

    def refresh_item(self, url : str, ID : int):
        refreshed = False
        while not refreshed :
            try:
                res = requests.put(url + "/refresh", params={"ID": ID})
                res.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
            except:
                print(f"Connection Error\nRetrying connection\n")
            else:
                stat = res.json()
                if "Status" in stat and stat["Status"] == True:
                    refreshed = True
                    print(f"Refreshed correctly to the Catalog; myID = {ID}\n")
                else:
                    print(stat)

class GenericService(): 
    def __init__(self, Service_info : ServiceInfo, ServiceCatalog_url : str) :
        self.Service_info = Service_info
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ID = self.register(self.Service_info.__dict__())
        self.Thread = RefreshThread(self.ServiceCatalog_url, self.ID)
        self.Thread.start()

    def register(self, info : dict) -> int:
        while True:
            try:
                res = requests.post(self.ServiceCatalog_url + "/insert", json = info)
                res.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:                    
                    ID = res.json()["ID"]
                    print(f"Registered correctly to the ServiceCatalog.\nID: {ID}\n")
                    return ID
                except:
                    print(f"Error in the response\n")

class GenericMQTTResource():
    def __init__(self, ResourceInfo, CompanyInfo : dict, ServiceCatalog_url : str) :        
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        self.ResourceInfo = ResourceInfo

        if CompanyInfo is not None and "CompanyName" in CompanyInfo and "CompanyToken" in CompanyInfo:
            self.CompanyInfo = {
                "CompanyName" : CompanyInfo["CompanyName"],
                "CompanyToken" : CompanyInfo["CompanyToken"]
            }
        else:
            raise InfoException("CompanyInfo is not valid")

        #Register
        self.ID = self.register_device(self.ResourceInfo.__dict__())
        self.Thread = RefreshThread(self.ResourceCatalog_url, self.ID)
        self.Thread.start()
        
        #MQTT client
        self.MQTTclient_start()

    def MQTTclient_start(self):
        self.BrokerIP, self.BrokerPort, self.baseTopic = self.get_broker() 
        self.client = MyMQTT(f"{self.baseTopic}_ID{self.ID}", self.BrokerIP, self.BrokerPort, self)
        self.client.start()

    def register_device(self, info : dict) -> int:
        while True:
            try:
                res = requests.post(self.ResourceCatalog_url + "/insert/device", params=self.CompanyInfo, json = info)
                res.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:                    
                    ID = res.json()["ID"]
                    print(f"Registered correctly to the ServiceCatalog.\nID: {ID}\n")
                    return ID
                except:
                    print(f"Error in the response\n")

    def get_ResourceCatalog_url(self) :
        while True:
            try:
                res = requests.get(self.ServiceCatalog_url + "/search/serviceName", params = {"serviceName": "ResourceCatalog"})
                res.raise_for_status()
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    res_dict = res.json()[0]
                    serviceDetails = res_dict["servicesDetails"]
                    for services in serviceDetails:
                        if services["serviceType"] == "REST":
                            return services["serviceIP"]
                except:
                    print(f"Error in the Resource information\nRetrying connection\n")
                    time.sleep(1)
                    
    def get_broker(self) :
        while True:
            try:
                res = requests.get(self.ServiceCatalog_url + "/broker")
                res.raise_for_status()
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    broker = res.json()
                    return broker["IP"], broker["port"], broker["baseTopic"]
                except:
                    print(f"Error in the broker information\nRetrying connection\n")
                    time.sleep(1)

    def stop(self):
        self.Thread.stop()
        self.client.stop()