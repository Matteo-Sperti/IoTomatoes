import requests
import time
import json
import paho.mqtt.client as PahoMQTT

from ItemInfo import * 
from MyExceptions import InfoException
from MyThread import MyThread

class RefreshThread(MyThread):
    def __init__(self, url : str, ID : int, interval=60, CompanyInfo : dict = {}):
        """RefreshThread class. Refresh the Catalog every ``interval`` seconds.
        
        ``url {str}``: Catalog URL.\n
        ``ID {int}``: ID of the item.\n
        ``interval {int}``: refresh interval in seconds (default = 60).\n
        ``CompanyInfo {dict}``: Company information (default = {}), needed only if the item is a resource.
        """
        super().__init__(self.refresh_item, (url, ID, CompanyInfo), interval)

    def refresh_item(self, url : str, ID : int, CompanyInfo : dict = {}):
        """Refresh item ``ID`` in the Catalog at ``url``."""

        refreshed = False
        while not refreshed :
            try:
                res = requests.put(url + "/refresh", params={"ID": ID}.update(CompanyInfo))
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

class GenericEndpoint(): 
    def __init__(self, settings : dict, isService : bool = False, 
                    isResource : bool = True, CompanyInfo : dict = {}) :
        """GenericEndpoint class. It is the base class for all the endpoints."""

        if "ServiceCatalog_url" not in settings:
            raise InfoException("The Service Catalog URL is missing")
        self.ServiceCatalog_url = settings["ServiceCatalog_url"]
        if isService ^ isResource:
            raise InfoException("The Endpoint must be a service or a resource, not both or none")
        else:
            self._isService = isService
            self._isResource = isResource
            self.EndpointInfo, self._CompanyInfo = construct(settings, CompanyInfo, isService, isResource)
            self._MQTTclient = isMQTT(self.EndpointInfo)
            self._subscribedTopics = subscribedTopics(self.EndpointInfo)

    def start(self):
        if self._isService:
            self.start_as_a_service()
        elif self._isResource:
            self.start_as_a_resource()

        if self._MQTTclient:
            self.start_MQTTclient()

    def stop(self):
        self._RefreshThread.stop()

        if self._MQTTclient:
            self.unsubscribe_all()
            self._paho_mqtt.loop_stop()
            self._paho_mqtt.disconnect()

    def start_as_a_service(self) :
        self.ID = self.register_service()
        self._RefreshThread = RefreshThread(self.ServiceCatalog_url, self.ID)

    def register_service(self) -> int:
        while True:
            try:
                res = requests.post(self.ServiceCatalog_url + "/insert", json = self.EndpointInfo)
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

    def start_as_a_resource(self) :        
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        #Register
        self.ID = self.register_device()
        self._RefreshThread = RefreshThread(self.ResourceCatalog_url, self.ID, CompanyInfo = self._CompanyInfo)

    def register_device(self) -> int:
        while True:
            try:
                res = requests.post(self.ResourceCatalog_url + "/insert/device", 
                                        params=self._CompanyInfo, json = self.EndpointInfo)
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
                res = requests.get(self.ServiceCatalog_url + "/search/serviceName", 
                                    params = {"serviceName": "ResourceCatalog"})
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

    def start_MQTTclient(self) :
        self._MQTTclient = True
        self._broker, self._port, self._baseTopic = self.get_broker()
        self.MQTTclientID = f"IoTomatoes_ID{self.ID}"
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(self.MQTTclientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        # manage connection to broker
        self._paho_mqtt.connect(self._broker, self._port)
        self._paho_mqtt.loop_start()
        # subscribe the topics
        for topic in self._subscribedTopics:
            self.mySubscribe(self._baseTopic + topic)

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self._broker, rc))

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        # A new message is received
        self.notify(msg.topic, msg.payload) # type: ignore

    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def mySubscribe(self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        print("subscribed to %s" % (topic))

    def unsubscribe_all(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            for topic in self._subscribedTopics:
                self._paho_mqtt.unsubscribe(self._baseTopic + topic)