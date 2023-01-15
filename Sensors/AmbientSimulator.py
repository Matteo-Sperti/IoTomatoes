import random
import json
import paho.mqtt.client as PahoMQTT
import sys

sys.path.append('../SupportClasses/')
from MyThread import MyThread

noiseAmplitude = 1
brokerIP = "mqtt.eclipseprojects.io"
brokerPort = 1883
baseTopic =  "IoTomatoes/"

class AmbientSimulator():
    def __init__(self, CompanyName : str, fieldNumber : int):
        self._CompanyName = CompanyName
        self._fieldNumber = fieldNumber
        self._subscribedTopics = [
            f"Devices/{self._CompanyName}/{self._fieldNumber}/+/led", 
            f"Devices/{self._CompanyName}/{self._fieldNumber}/+/pump"
            ]
        self._temperature = 20
        self._humidity = 50
        self._light = 100
        self._soilMoisture = 50
        self._led = False
        self._pump = False

        self.UpdateThread = MyThread(self.update, 5)

    def start(self):
        self.start_MQTTclient()

    def stop(self):
        self.unsubscribe_all()
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
        self.UpdateThread.stop()

    def update(self):
        if self._led:
            self._light = 150 + 10*self.noiseValue()
        else:
            self._light = 40 + 10*self.noiseValue()

        if self._pump:
            self._soilMoisture += (2 + self.noiseValue())
            self._humidity += (1 + 0.2*self.noiseValue())
        else:
            self._soilMoisture -= (0.5 + self.noiseValue())
            self._humidity -= (0.1 + 0.1*self.noiseValue())

        self._temperature += (0.1 + 0.1*self.noiseValue())

    def get_temperature(self):
        return self._temperature + self.noiseValue()

    def get_humidity(self):
        return self._humidity + self.noiseValue()

    def get_light(self):
        return self._light + self.noiseValue()
    
    def get_soilMoisture(self):
        return self._soilMoisture + self.noiseValue()

    def noiseValue(self):
        amp = random.random()*noiseAmplitude
        if random.randint(0, 1) == 0:
            return amp
        else:
            return -amp

    def start_MQTTclient(self) :
        """Start the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """
        self._broker, self._port, self._baseTopic = brokerIP, brokerPort, baseTopic
        self.MQTTclientID = f"Ambient_{self._fieldNumber}"
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

        topic, msg_dict = msg.topic, json.loads(msg.payload)
        topic_list = topic.split("/")
        actuator = topic_list[-1]

        if actuator == "led":
            if msg_dict["e"][-1]["v"] == 1:
                self._led = True
            else:
                self._led = False
        elif actuator == "pump":
            if msg_dict["e"][-1]["v"] == 1:
                self._led = True
            else:
                self._led = False

    def mySubscribe(self, topic):
        """It subscribes to `topic`"""

        # subscribe for a topic
        print(topic)
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