import datetime
import json
import paho.mqtt.client as PahoMQTT

brokerIP = "mqtt.eclipseprojects.io"
brokerPort = 1883
baseTopic =  "IoTomatoes/"

class Listener():
    def __init__(self):
        self._broker, self._port, self._baseTopic = brokerIP, brokerPort, baseTopic
        self.topic = self._baseTopic + "#"

    def stop(self):
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

    def start(self) :
        """Start the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """
        self._broker, self._port, self._baseTopic = brokerIP, brokerPort, baseTopic
        self.MQTTclientID = f"ListenEverithing"

        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(self.MQTTclientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        # manage connection to broker
        self._paho_mqtt.connect(self._broker, self._port)
        self._paho_mqtt.loop_start()
        # subscribe the topics

        self.mySubscribe(self.topic)

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
        print(f"\n\nTIME: {datetime.datetime.now()}\nTOPIC: {topic}\nMESSAGE:\n{msg_dict}\n")

    def mySubscribe(self, topic):
        """It subscribes to `topic`"""

        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        print("Subscribed to %s" % (topic))

if __name__ == "__main__":
    listener = Listener()
    listener.start()
    input("Press Enter to stop listening...")

    listener.stop()
    print("Listening stopped")