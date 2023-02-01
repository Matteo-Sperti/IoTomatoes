import requests
import time
import json
import paho.mqtt.client as PahoMQTT

from ItemInfo import * 
from MyExceptions import InfoException
from MyThread import MyThread

class RefreshThread(MyThread):
    def __init__(self, url : str, ID : int, interval=60, CompanyInfo : dict = {}, SystemToken : str = ""):
        """RefreshThread class. Refresh the Catalog every `interval` seconds.
        
        `url {str}`: Catalog URL.\n
        `ID {int}`: ID of the item.\n
        `interval {int}`: refresh interval in seconds (default = 60).\n
        `CompanyInfo {dict}`: Company information (default = {}), needed only if the item is a resource.
        """
        super().__init__(self.refresh_item, (url, ID, CompanyInfo, SystemToken), interval)

    def refresh_item(self, url : str, ID : int, CompanyInfo : dict, SystemToken : str):
        """Refresh item `ID` in the Catalog at `url`."""

        refreshed = False
        while not refreshed :
            try:
                param = CompanyInfo.copy()
                param.update({"ID": ID})
                if SystemToken != "":
                    param.update({"SystemToken": SystemToken})
                res = requests.put(url + "/refresh", params=param)
                res.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                stat = res.json()
                if "Status" in stat and stat["Status"] == True:
                    refreshed = True
                    print(f"Refreshed correctly to the Catalog; myID = {ID}\n")
                else:
                    print(stat)
                    time.sleep(1)

class GenericEndpoint(): 
    def __init__(self, settings : dict, isService : bool = False, 
                    isResource : bool = False) :
        """GenericEndpoint class. It is the base class for all the endpoints.
        
        `settings {dict}`: dictionary containing the settings of the endpoint.\n
        `isService {bool}`: True if the endpoint is a service, False otherwise (default = False).\n
        `isResource {bool}`: True if the endpoint is a resource, False otherwise (default = False).
        `isService` and `isResource` are mutually exclusive.
        """

        if "ServiceCatalog_url" not in settings:
            raise InfoException("The Service Catalog URL is missing")
        self.ServiceCatalog_url = settings["ServiceCatalog_url"]
        if not isService ^ isResource:
            raise InfoException("The Endpoint must be a service or a resource, not both or none")
        else:
            self._isService = isService
            self._isResource = isResource
            self._EndpointInfo, self._CompanyInfo = construct(settings, isService, isResource)
            if isService :
                if "SystemToken" in settings:
                    self._SystemToken = settings["SystemToken"]
                else:
                    raise InfoException("The System Token is missing")
            
            self.start()


    def start(self):
        """Start the endpoint."""

        if self._isService:
            self.start_as_a_service()
        elif self._isResource:
            self.start_as_a_resource()

        self._MQTTclient = isMQTT(self._EndpointInfo)
        if self._MQTTclient:
            self._subscribedTopics = subscribedTopics(self._EndpointInfo)
            self.start_MQTTclient()

    def stop(self):
        """Stop the endpoint."""

        self._RefreshThread.stop()

        if self._MQTTclient:
            self.unsubscribe_all()
            self._paho_mqtt.loop_stop()
            self._paho_mqtt.disconnect()

    def start_as_a_service(self) :
        """ Start the endpoint as a service.
        It registers the service to the Service Catalog and starts the RefreshThread."""

        self.ID = self.register_service()
        self._RefreshThread = RefreshThread(self.ServiceCatalog_url, self.ID, SystemToken = self._SystemToken)
        if self._EndpointInfo["serviceName"] != "ResourceCatalog":
            self.ResourceCatalog_url = self.get_ResourceCatalog_url()

    def register_service(self) -> int:
        """Register the service to the Service Catalog."""

        while True:
            try:
                res = requests.post(self.ServiceCatalog_url + "/insert", 
                                        params={"SystemToken": self._SystemToken}, json = self._EndpointInfo)
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
        """ Start the endpoint as a resource.
        It registers the resource to the Resource Catalog and starts the RefreshThread."""

        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        #Register
        self.ID = self.register_device()
        self._EndpointInfo = self.get_device_info()
        self._RefreshThread = RefreshThread(self.ResourceCatalog_url, self.ID, CompanyInfo = self._CompanyInfo)


    def register_device(self) -> int:
        """Register the resource to the Resource Catalog."""

        while True:
            try:
                res = requests.post(self.ResourceCatalog_url + "/insert/device", 
                                        params=self._CompanyInfo, json = self._EndpointInfo)
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

    def get_device_info(self) -> dict:
        """Get the information of the resource from the Resource Catalog."""

        while True:
            try:
                res = requests.get(self.ResourceCatalog_url + "/get", 
                                    params = {"ID": self.ID, **self._CompanyInfo})
                res.raise_for_status()
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    return res.json()
                except:
                    print(f"Error in the Resource information\nRetrying connection\n")
                    time.sleep(1)

    def get_ResourceCatalog_url(self) :
        """Get the URL of the Resource Catalog from the Service Catalog."""

        while True:
            try:
                params = {"SystemToken": self._SystemToken, "serviceName": "ResourceCatalog"}
                res = requests.get(self.ServiceCatalog_url + "/search/serviceName", params = params)
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
        """Get the broker information from the Service Catalog."""

        while True:
            try:
                params = {"SystemToken": self._SystemToken}
                res = requests.get(self.ServiceCatalog_url + "/broker", params=params)
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
        """Start the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """
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
        time.sleep(1)
        # subscribe the topics
        for topic in self._subscribedTopics:
            self.mySubscribe(self._baseTopic + topic)

    def myOnConnect(self,client,userdata,flags,rc):
        """It provides information about Connection result with the broker"""

        dic={
            "0":f"Connection successful to {self._broker}",
            "1":f"Connection to {self._broker} refused - incorrect protocol version",
            "2":f"Connection to {self._broker} refused - invalid client identifier",
            "3":f"Connection to {self._broker} refused - server unavailable",
        }             
        print(dic[str(rc)])

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        """When a message is received, it is processed by this callback. 
        It redirects the message to the notify method (which must be implemented by the user)"""

        # A new message is received
        self.notify(msg.topic, json.loads(msg.payload)) # type: ignore

    def myPublish(self, topic, msg):
        """It publishes a dictionary message `msg` in `topic`"""

        # publish a message with a certain topic
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def mySubscribe(self, topic):
        """It subscribes to `topic`"""

        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        print("Subscribed to %s" % (topic))

    def unsubscribe_all(self):
        """It unsubscribes all the topics"""

        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            for topic in self._subscribedTopics:
                self._paho_mqtt.unsubscribe(self._baseTopic + topic)