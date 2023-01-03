import requests
import time
import json
import paho.mqtt.client as PahoMQTT

from ItemInfo import ServiceInfo
from MyExceptions import InfoException
from MyThread import MyThread

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
        self.client = GenericMQTTEndpoint(f"IoTomatoes_ID{self.ID}",self.ServiceCatalog_url, self)

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

class GenericMQTTEndpoint():
    def __init__(self, clientID, ServiceCatalog_url : str, notifier) :
        self.ServiceCatalog_url = ServiceCatalog_url
        self.broker, self.port, self.baseTopic = self.get_broker()
        self.notifier = notifier
        self.clientID = clientID
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self.start()

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

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.broker, rc))

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # A new message is received
        self.notifier.notify(msg.topic, msg.payload) # type : ignore

    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def mySubscribe(self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        self._topic = topic
        print("subscribed to %s" % (topic))

    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def unsubscribe(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

    def stop(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
