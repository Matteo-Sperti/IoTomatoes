import time
import json
import Adafruit_DHT

from GenericEndpoint import GenericResource
from ItemInfo import *

sensor = Adafruit_DHT.DHT11

class RasPySensor(GenericResource):
    def __init__(self, DeviceInfo : dict):
        """Constructor of the Raspberry Pi sensor. It will initialize the sensor and
        the MQTT client, it will register the sensor to the ResourceCatalog and to the broker 
        and it will subscribe to the topics specified in the ResourceCatalog."""

        super().__init__(DeviceInfo)

        self.pin = settings["PIN_IN"]

        self._message = {
            "cn" : self.CompanyName,
            "bn" : 0,
            "field" : self.field,
            "e" : [{
                "n": "",
                "v": None,
                "u": "",       
                "t": None
            }]
        }

    def get_measures(self):
        """This function is called periodically in order to get the sensor readings.
        It will publish the readings on the topics specified in the ResourceCatalog.
        
        In this example, the sensor is a DHT11 temperature and humidity sensor."""

        humidity_topic = None
        temperature_topic = None
        for topic in publishedTopics(self._EndpointInfo):
            if topic.split('/')[-1] == "humidity":
                humidity_topic = topic
            elif topic.split('/')[-1] == "temperature":
                temperature_topic = topic

        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, self.pin)

        if humidity is not None and humidity_topic is not None:
            message = self.construct_message("humidity", "%")
            message["e"][-1]["v"] = humidity
            self.myPublish(humidity_topic, message)

        if temperature is not None and temperature_topic is not None:
            message = self.construct_message("temperature", "C")
            message["e"][-1]["v"] = temperature
            self.myPublish(temperature_topic, message)

    def notify(self, topic, msg):
        """Callback function called when a message is received from the broker.
        If the resource is an actuator, it will turn it on or off 
        depending on the message received
        """
        print(f"{self.ID} received {msg} on topic {topic}")

        if self.isActuator:
            actuator_info = actuatorType(self._EndpointInfo)
            actuator_topic = topic.split("/")[-1]

            if actuator_topic in actuator_info:
                try:
                    state = msg["e"][-1]["v"]
                except KeyError:
                    print("Message not valid")
                else:
                    if state == 0:
                        print(f"Resource {self.ID}: {actuator_topic} turned OFF")
                        # If a real actuator is connected to the Raspberry Pi, 
                        # here it should be turned OFF
                    elif state == 1:
                        print(f"Resource {self.ID}: {actuator_topic} turned ON")
                        # If a real actuator is connected to the Raspberry Pi, 
                        # here it should be turned ON
                    else:
                        print(f"Resource {self.ID}: {actuator_topic} state not valid")
            else:
                print(f"Resource {self.ID}: {actuator_topic} not found")

    
    def construct_message(self, measure : str, unit : str) :
        """Constructs a message to be sent to the broker using the SenML format"""

        message=self._message.copy()
        message["bn"]=self.ID
        message["e"][-1]["n"] = measure
        message["e"][-1]["v"] = 0
        message["e"][-1]["t"] = time.time()
        message["e"][-1]["u"] = unit
        return message

if __name__ == "__main__":
    try:
        settings = json.load(open("DeviceSettings.json"))
        IoTSensor = RasPySensor(settings)

        measureTimeInterval = settings["measureTimeInterval"]
    except Exception as e:
        print(e)
    else:
        while True:
            IoTSensor.get_measures()
            time.sleep(measureTimeInterval)