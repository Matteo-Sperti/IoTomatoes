import random
import paho.mqtt.client as PahoMQTT
import json
from .MyThread import MyThread

noiseAmplitude = 1


class AmbientSimulator():
    def __init__(self, CompanyName: str, fieldNumber: int, broker: str, port: int = 1883):
        """Simulates the ambient. Initialize the values of the sensors 
        and the actuators"""

        self._temperature = 20
        self._humidity = 50
        self._light = 50000
        self._soilMoisture = 50

        self._led = False
        self._pump = False

        self.broker = broker
        self.port = port
        self.baseTopic = f"{CompanyName}/{fieldNumber}"
        self.fieldNumber = fieldNumber
        self.UpdateThread = MyThread(self.update, 5)

    def stop(self):
        """Stop the thread that updates the values of the sensors"""
        self.UpdateThread.stop()
        self.stopMQTT()

    def update(self):
        """Update the values of the sensors according 
            to the state of the actuators"""

        if self._led:
            self._light = self._light + 1000 + 100*self.noiseValue()
        else:
            self._light = self._light - 100 - 100*self.noiseValue()

        if self._pump:
            self._soilMoisture += (0.5 + 0.02*self.noiseValue())
            self._humidity += (0.1 + 0.02*self.noiseValue())
        else:
            self._soilMoisture -= (0.05 + 0.01*self.noiseValue())
            self._humidity -= (0.01 + 0.01*self.noiseValue())

        self._temperature += (0.1 + 0.1*self.noiseValue())

        self._soilMoisture = self.saturate(self._soilMoisture, 0, 100)
        self._humidity = self.saturate(self._humidity, 0, 100)
        self._light = self.saturate(self._light, 10, 100000)

    def saturate(self, value, min, max):
        """Saturate the value between min and max"""
        if value > max:
            value = max
        elif value < min:
            value = min
        return value

    def get_temperature(self):
        return self._temperature + self.noiseValue()

    def get_humidity(self):
        return self._humidity + self.noiseValue()

    def get_light(self):
        return self._light + self.noiseValue()

    def get_soilMoisture(self):
        return self._soilMoisture + self.noiseValue()

    def noiseValue(self):
        """Return a random value between -noiseAmplitude and noiseAmplitude"""

        return random.uniform(-noiseAmplitude, noiseAmplitude)

    def setActuator(self, actuator: str, state: bool):
        """Set the state of the actuator"""

        if actuator == "led":
            self._led = state
        elif actuator == "pump":
            self._pump = state
        else:
            print("Actuator not valid")

    def startMQTT(self):
        """Starts the MQTT client.
        It subscribes the topics and starts the MQTT client loop.
        """

        self.MQTTclientID = f"AmbientSimulator_{random.randint(0,1000)}"
        self._isSubscriber = True
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(self.MQTTclientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()
        self._paho_mqtt.subscribe(f"{self.baseTopic}/+/led", 2)
        self._paho_mqtt.subscribe(f"{self.baseTopic}/+/pump", 2)

    def myOnConnect(self, client, userdata, flags, rc):
        """It provides information about Connection result with the broker"""

        dic = {
            "0": f"Connection successful to {self.broker}",
            "1": f"Connection to {self.broker} refused - incorrect protocol version",
            "2": f"Connection to {self.broker} refused - invalid client identifier",
            "3": f"Connection to {self.broker} refused - server unavailable",
        }
        print(dic[str(rc)])

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        """When a message is received, it is processed by this callback. 
        It redirects the message to the notify method (which must be implemented by the user)"""

        topic = msg.topic
        actuator_topic = topic.split("/")[-1]
        msgDict = json.loads(msg.payload)
        print(f"AmbientSimulator : Received message '{msgDict}' on topic '{topic}'")
        state = msgDict["e"][0]["v"]
        if state == 0:
            self.setActuator(actuator_topic, False)
        elif state == 1:
            self.setActuator(actuator_topic, False)

    def stopMQTT(self):
        """Stop the endpoint."""

        self._paho_mqtt.unsubscribe(
            [f"{self.baseTopic}/+/led",
             f"{self.baseTopic}/+/pump"])

        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
