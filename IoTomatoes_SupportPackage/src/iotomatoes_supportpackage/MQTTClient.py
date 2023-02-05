import time
import requests
import json

from iotomatoes_supportpackage.ItemInfo import subscribedTopics, publishedTopics

class BaseMQTTClient(): 
    def __init__(self, url : str, EndpointInfo: dict, broker : str = ""):
        """BaseMQTTClient class. It is the base class for the MQTT client.

        Arguments:\n
        `url (str)`: Catalog URL.\n
        `EndpointInfo (dict)`: Dictionary containing the information of the resource or service.\n
        `CompanyName (str)`: Name of the company.
        """

        self._url = url
        self._EndpointInfo = EndpointInfo
        self._broker = broker

    def stopMQTT(self):
        """Stop the endpoint."""

        self.unsubscribe_all()
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()                             

    def startMQTT(self) :
        """If the Endpoint is MQTT, starts the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """

        import paho.mqtt.client as PahoMQTT

        broker, self._port, self._baseTopic = self.get_broker()
        if self._broker == "":
            self._broker = broker
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
    def subscribedTopics(self) -> list:
        return subscribedTopics(self._EndpointInfo)

    @property
    def publishedTopics(self) -> list:
        return publishedTopics(self._EndpointInfo)