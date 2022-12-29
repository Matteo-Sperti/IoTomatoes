import requests
import json
import time
import threading
from MyMQTT import MyMQTT

class EndPoint():
    def __init__(self, info : dict, url : str) :
        self.CatalogUrl = url
        self.ID = self.register(info)

        self._stop = threading.Event()
        self.RefreshThread = threading.Thread()
        self.RefreshThread.daemon = True
        self.RefreshThread.start()

    def close(self) :
        self._stop.set()
        self.RefreshThread.join()

    def stopped(self):
        return self._stop.isSet()

    def run(self) :
        while True :
            if self.stopped():
                return
            print (f"Refreshing {self.ID}\n")
            refreshed = False
            while not refreshed:
                res = requests.put(self.CatalogUrl + "/refresh", params={"ID": self.ID})
                print("Richiesta fatta")
                if res.status_code == 200:
                    stat = res.json()
                    if "Status" in stat and stat["Status"] == True:
                        refreshed = True
                        print(f"Refreshed {self.ID}\n")
                    else:
                        print(f"Error in the response\n")
            time.sleep(60)

    def register(self, Service_info : dict) :
        while True:
            try:
                res = requests.post(self.CatalogUrl + "/insert", json = Service_info)
                res.raise_for_status()
            except requests.exceptions.ConnectionError:
                print(f"Connection Error\nRetrying connection\n")
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as err:
                 print(f"{err.response.status_code} : {err.response.reason}")
            else:
                try:                    
                    ID = res.json()["ID"]
                    print(f"Registered {ID}\n")
                    return ID
                except:
                    print(f"Error in the response\n")

class GenericService(EndPoint): 
    def __init__(self, Service_info : dict, ServiceCatalog_url : str) :
        self.Service_info = Service_info
        super().__init__(Service_info, ServiceCatalog_url)

class GenericResource(EndPoint):  
    def __init__(self, Resource_info : dict, ServiceCatalog_url : str) :
        self.ServiceCatalog_url = ServiceCatalog_url
        self.Resource_info = Resource_info
        super().__init__(Resource_info, self.get_ResourceCatalog_url())

    def get_ResourceCatalog_url(self) :
        while True:
            try:
                res = requests.get(self.CatalogUrl + "7search/serviceName", params = {"serviceName": "ResourceCatalog"})
                res.raise_for_status()
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
            else:
                try:
                    for services in res.json()["servicesDetails"]:
                        if services["serviceType"] == "REST":
                            return services["serviceIP"]
                except KeyError:
                    print(f"Error in the Resource information\nRetrying connection\n")

class GenericMQTTResource(GenericResource):
    def __init__(self, ServiceCatalog_url : str) :
        
        ResourceInfo = {
            "deviceName": "",
            "companyName": "",
            "deviceType": "",
            "PowerConsumption_kW" : 0,
            "measureType": [],
            "availableServices": [
                "MQTT",
                "REST"
            ],
            "servicesDetails": [
                {
                    "serviceType": "MQTT",
                    "topic": []
                },
                {
                    "serviceType": "REST",
                    "serviceIP": "dht11.org:8080"
                }
            ],
        }
        
        super().__init__(ResourceInfo, ServiceCatalog_url)
        self.BrokerIP, self.BrokerPort, self.baseTopic = self.get_broker(ServiceCatalog_url) 
        self.client = MyMQTT(self.ID, self.BrokerIP, self.BrokerPort, self)

    def get_broker(self, ServiceCatalog_url : str) :
        while True:
            try:
                res = requests.get(ServiceCatalog_url + "/broker")
                res.raise_for_status()
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as HTTPError:
                print(f"{HTTPError.response.status_code}: {HTTPError.response.title}\n")
            else:
                broker = res.json()
                return broker["IP"], broker["port"], broker["baseTopic"]

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")

class GenericSensor(GenericMQTTResource):
    def __init__(self, ServiceCatalog_url : str) :
        super().__init__(ServiceCatalog_url)
        self.client.start()
        self.client.mySubscribe(self.baseTopic + "/#")

class GenericActuator(GenericMQTTResource):
    def __init__(self, ServiceCatalog_url : str) :
        super().__init__(ServiceCatalog_url)
        self.client.start()

    def publish(self, topic, msg):
        self.client.myPublish(self.baseTopic + "/" + topic, msg)

class GenericUser(GenericMQTTResource):
    def __init__(self, ServiceCatalog_url : str) :
        super().__init__(ServiceCatalog_url)
        self.client.start()
        self.client.mySubscribe(self.baseTopic + "/#")

    def publish(self, topic, msg):
        self.client.myPublish(self.baseTopic + "/" + topic, msg)


if __name__ == "__main__":
    Service_info = json.load(open("new_service.json"))
    ServiceCatalog_url = "http://localhost:8080/ServiceCatalog/"
    serv = GenericService(Service_info, ServiceCatalog_url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Closing")
        serv.close()
