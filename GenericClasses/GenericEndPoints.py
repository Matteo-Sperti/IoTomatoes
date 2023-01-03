import requests
import json
import time
import threading
from MyMQTT import MyMQTT
from ItemInfo import ServiceInfo

class RefreshThread(object):
    def __init__(self, url: str, ID : int):
        self._stop = threading.Event()
        self.t = threading.Thread(target=self.run_forever, args=(url, ID))
        self.t.start()

    def close(self) :
        self._stop.set()
        self.t.join()

    def stopped(self):
        return self._stop.is_set()

    def run_forever(self, url: str, ID : int) :
        while True :
            if self.stopped():
                print("RefreshThread stopped")
                return
            refreshed = False
            try:
                res = requests.put(url + "/refresh", params={"ID": ID})
                res.raise_for_status()
            except requests.exceptions.ConnectionError:
                print(f"Connection Error\nRetrying connection\n")
            except requests.exceptions.Timeout:
                print(f"Timeout\nRetrying connection\n")
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
            else:
                stat = res.json()
                if "Status" in stat and stat["Status"] == True:
                    refreshed = True
                    print(f"Refreshed {ID}\n")
                else:
                    print(stat)

            if refreshed:
                time.sleep(60)
            else:
                time.sleep(1)

def register(url: str, info : dict, isService : bool = False, isDevice : bool = False, isUser : bool = False) -> int:
    while True:
        try:
            if isService:
                res = requests.post(url + "/insert", json = info)
                res.raise_for_status()
            elif isDevice:
                res = requests.post(url + "/insert/device", json = info)
                res.raise_for_status()
            elif isUser:
                res = requests.post(url + "/insert/user", json = info)
                res.raise_for_status()
            else:
                raise Exception("A service, device or user must be specified")
        except requests.exceptions.ConnectionError:
            print(f"Connection Error\nRetrying connection\n")
            time.sleep(1)
        except requests.exceptions.HTTPError as err:
            print(f"{err.response.status_code} : {err.response.reason}")
            time.sleep(1)
        except:
            print(f"Error in the request\n")
            time.sleep(1)
        else:
            try:                    
                ID = res.json()["ID"]
                print(f"Registered ID: {ID}\n")
                return ID
            except:
                print(f"Error in the response\n")

class GenericService(): 
    def __init__(self, Service_info : ServiceInfo, ServiceCatalog_url : str) :
        self.Service_info = Service_info
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ID = register(self.ServiceCatalog_url, self.Service_info.__dict__(), isService=True)
        self.Thread = RefreshThread(self.ServiceCatalog_url, self.ID)

class GenericMQTTResource():
    def __init__(self, info, ServiceCatalog_url : str, isDevice : bool = False, isUser : bool = False) :        
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        self.info = info

        #Register
        self.ID = register(self.ResourceCatalog_url, self.info.__dict__(), isDevice=isDevice, isUser=isUser)
        self.Thread = RefreshThread(self.ResourceCatalog_url, self.ID)
        
        #MQTT client
        self.MQTTclient_start()

    def MQTTclient_start(self):
        self.BrokerIP, self.BrokerPort, self.baseTopic = self.get_broker() 
        self.client = MyMQTT(f"{self.baseTopic}_ID{self.ID}", self.BrokerIP, self.BrokerPort, self)
        self.client.start()

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
                except KeyError:
                    print(f"Error in the Resource information\nRetrying connection\n")
                    
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
                except KeyError:
                    print(f"Error in the broker information\nRetrying connection\n")
                    time.sleep(1)

    def stop(self):
        self.Thread.close()
        self.client.stop()

if __name__ == "__main__":
    Service_info = json.load(open("new_service.json"))
    ServiceCatalog_url = Service_info["ServiceCatalog_url"]
    serv = GenericService(Service_info, ServiceCatalog_url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        serv.Thread.close()
