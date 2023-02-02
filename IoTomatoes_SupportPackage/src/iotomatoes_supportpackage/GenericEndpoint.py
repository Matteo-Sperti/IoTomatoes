import requests
import time
import json

from iotomatoes_supportpackage.ItemInfo import (
    isMQTT, subscribedTopics, publishedTopics, getIPaddress)
from iotomatoes_supportpackage.MyExceptions import InfoException
from iotomatoes_supportpackage.MyThread import MyThread

class RefreshThread(MyThread):
    def __init__(self, url : str, endpoint, interval=60, **kwargs):
        """RefreshThread class. Refresh the Catalog every `interval` seconds.
        
        `url {str}`: Catalog URL.\n
        `ID {int}`: ID of the item.\n
        `interval {int}`: refresh interval in seconds (default = 60).\n
        `CompanyInfo {dict}`: Company information (default = {}), needed only if the item is a resource.
        """

        self._url = url
        self.endpoint = endpoint
        super().__init__(self.refresh_item, interval, **kwargs)


    def refresh_item(self, **kwargs):
        """Refresh item `ID` in the Catalog at `url`."""
        refreshed = False
        while not refreshed :
            try:
                param = {"ID": self.endpoint.ID}
                if "CompanyInfo" in kwargs:
                    param.update(kwargs["CompanyInfo"])
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
                        print(f"Refreshed correctly to the Catalog; myID = {self.endpoint.ID}\n")
                    else:
                        # problem in the Catalog, maybe the item has been deleted
                        # register again
                        print(f"Error in the Catalog, trying to register again\n")
                        self.endpoint.restart()
                else:
                    print(stat)
                    time.sleep(1)

class GenericMQTTClient(): 
    def __init__(self, url : str, EndpointInfo: dict, CompanyName : str = ""):
        """GenericMQTTClient class. It is the base class for the MQTT client.

        Arguments:\n
        `url (str)`: Catalog URL.\n
        `EndpointInfo (dict)`: Dictionary containing the information of the resource or service.\n
        `CompanyName (str)`: Name of the company.
        """

        self._url = url
        self._EndpointInfo = EndpointInfo
        self._CompanyName = CompanyName

    def stopMQTT(self):
        """Stop the endpoint."""
        if self.isMQTT:
            self.unsubscribe_all()
            self._paho_mqtt.loop_stop()
            self._paho_mqtt.disconnect()                             

    def startMQTT(self) :
        """If the Endpoint is MQTT, starts the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """
        if self.isMQTT:
            import paho.mqtt.client as PahoMQTT

            self._broker, self._port, self._baseTopic = self.get_broker()
            self.MQTTclientID = f"IoTomatoes_ID{self._EndpointInfo['ID']}"
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
            for topic in self.subscribedTopics:
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
        self._paho_mqtt.publish(self._baseTopic + topic, json.dumps(msg), 2)

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
            for topic in self.subscribedTopics:
                self._paho_mqtt.unsubscribe(self._baseTopic + topic)

    def get_broker(self):
        """Get the broker information from the Service Catalog."""

        while True:
            try:
                res = requests.get(self._url + "/broker")
                res.raise_for_status()
                broker = res.json()
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    return broker["IP"], broker["port"], broker["baseTopic"]
                except:
                    print(f"Error in the broker information\nRetrying connection\n")
                    time.sleep(1)

    @property
    def isMQTT(self) -> bool:
        return isMQTT(self._EndpointInfo)

    @property
    def subscribedTopics(self) -> list:
        return subscribedTopics(self._EndpointInfo)

    @property
    def publishedTopics(self) -> list:
        return publishedTopics(self._EndpointInfo)


class GenericService() :
    def __init__(self, settings: dict):
        """Initialize the GenericService class.
        It gets the System Token from the settings and calls the GenericEndpoint constructor.
        """
        self.ServiceCatalog_url = settings["ServiceCatalog_url"]
        self.start()
        self._MQTTClient = GenericMQTTClient(self.ServiceCatalog_url, self._EndpointInfo)
        self._MQTTClient.startMQTT()

    def getCompaniesList(self):
        """Return the complete list of the companies from the Resource Catalog""" 

        try:
            r = requests.get(self.ResourceCatalog_url+"/all")
            r.raise_for_status()
            companyList = r.json()
        except:
            print("ERROR: Resource Catalog not reachable!")
            return []
        else:
            return companyList

    def start(self) :
        """ Start the endpoint as a service.
        It registers the service to the Service Catalog and starts the RefreshThread."""

        self._EndpointInfo = self.register()
        self._RefreshThread = RefreshThread(self.ServiceCatalog_url, self)
        if self.serviceName != "ResourceCatalog":
            self.ResourceCatalog_url = self.getOtherServiceURL("ResourceCatalog")

    def restart(self):
        self.start()
        self._MQTTClient = GenericMQTTClient(self.ServiceCatalog_url, self._EndpointInfo)
        self._MQTTClient.startMQTT()

    def stop(self):
        self._RefreshThread.stop()
        self._MQTTClient.stopMQTT()

    def register(self) -> dict:
        """Register the service to the Service Catalog."""

        while True:
            try:
                res = requests.post(self.ServiceCatalog_url + "/insert", 
                                        json = self._EndpointInfo)
                res.raise_for_status()
                res_dict = res.json()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:                    
                    if "ID" in res_dict:
                        print("Service registered to the Service Catalog")
                        return res_dict
                except:
                    print(f"Error in the response\n")  

    def getOtherServiceURL(self, serviceName:str):
        """Return the URL of the service `serviceName`"""

        try:
            r = requests.get(self.ServiceCatalog_url+"/" + serviceName + "/url")
            r.raise_for_status()
            servicesList = r.json()
        except:
            print("ERROR: Service Catalog not reachable!")
            return ""
        else:
            if len(servicesList) == 0:
                print("ERROR: Service not found!")
                return ""
            else:
                serviceInfo = servicesList[0]
                print(serviceInfo)
                return getIPaddress(serviceInfo)
    
    @property
    def serviceName(self) -> str:
        return self._EndpointInfo["serviceName"]
    
    @property
    def ID(self) -> int:
        return self._EndpointInfo["ID"]
    
class GenericResource() :
    def __init__(self, settings: dict):
        """Initialize the GenericResource class."""

        self._CompanyName = settings["CompanyName"]
        self.platform_url = settings["IoTomatoes_url"]
        self.start()
        self._MQTTClient = GenericMQTTClient(self.platform_url, self._EndpointInfo, self._CompanyName)
        self._MQTTClient.startMQTT()

    def start(self) :        
        """ Start the endpoint as a resource.
        It registers the resource to the Resource Catalog and starts the RefreshThread."""

        self._EndpointInfo = self.register()
        self._RefreshThread = RefreshThread(self.platform_url + "/rc/", self, CompanyName=self._CompanyName)

    def restart(self):
        self.start()
        self._MQTTClient = GenericMQTTClient(self.platform_url, self._EndpointInfo, self._CompanyName)
        self._MQTTClient.startMQTT()

    def stop(self):
        self._RefreshThread.stop()
        self._MQTTClient.stopMQTT()

    def register(self) -> dict:
        """Register the resource to the Resource Catalog."""

        while True:
            try:
                res = requests.post(self.platform_url + "/rc/insert/device", 
                                        params=self._CompanyName, json = self._EndpointInfo)
                res.raise_for_status()
                res_dict = res.json()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:               
                if "ID" in res_dict:
                    print("Resource registered to the Resource Catalog")
                    return res_dict
                else:
                    print(f"Error in the response\n")
                    time.sleep(1)

    @property
    def ID(self) -> int:
        return self._EndpointInfo["ID"]
    
    @property
    def field(self) -> int:
        """Return the field of the resource."""
        try:
            return self._EndpointInfo["field"]
        except:
            return -1

    @property
    def isActuator(self) -> bool:
        if "isActuator" not in self._EndpointInfo:
            return False
        else:
            return self._EndpointInfo["isActuator"]

    @property
    def isSensor(self) -> bool:
        if "isSensor" not in self._EndpointInfo:
            return False
        else:
            return self._EndpointInfo["isSensor"]

    @property
    def measureType(self) -> list:
        if "measureType" not in self._EndpointInfo:
            raise InfoException("measureType is missing")
        else:
            return self._EndpointInfo["measureType"]

    @property
    def actuatorType(self) -> list:
        if "actuatorType" not in self._EndpointInfo:
            raise InfoException("actuatorType is missing")
        else:
            return self._EndpointInfo["actuatorType"]

    @property
    def PowerConsumption_kW(self) -> int:
        if "PowerConsumption_kW" not in self._EndpointInfo:
            raise InfoException("PowerConsumption_kW is missing")
        else:
            return self._EndpointInfo["PowerConsumption_kW"]

    def __str__(self):
        """Return a string with the information of the resource."""

        dict = {
            "ID": self.ID,
            "CompanyName": self._CompanyName,
            "EndpointInfo": self._EndpointInfo
        }

        return json.dumps(dict, indent=4)