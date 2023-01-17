import time
import json
import Adafruit_DHT

from GenericEndpoint import GenericResource
from ItemInfo import *

sensor = Adafruit_DHT.DHT11

pin = 17

class RasPySensor(GenericResource):
    def __init__(self, DeviceInfo : dict):
        super().__init__(DeviceInfo)
        self._message = {
            "cn" : getCompanyName(self._CompanyInfo),
            "bn" : 0,
            "field" : getField(self._EndpointInfo),
            "e" : [{
                "n": "",
                "v": None,
                "u": "",       
                "t": None
            }]
        }

    def run(self):
        humidity_topic = None
        temperature_topic = None
        for topic in publishedTopics(self._EndpointInfo):
            if topic.split('/')[-1] == "humidity":
                humidity_topic = topic
            elif topic.split('/')[-1] == "temperature":
                temperature_topic = topic

        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

        if humidity is not None and humidity_topic is not None:
            message = self.construct_message("humidity", "%")
            message["e"][-1]["v"] = humidity
            self.myPublish(humidity_topic, message)

        if temperature is not None and temperature_topic is not None:
            message = self.construct_message("temperature", "C")
            message["e"][-1]["v"] = temperature
            self.myPublish(temperature_topic, message)

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")
    
    def construct_message(self, measure : str, unit : str) :
        message=self._message
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
            IoTSensor.run()
            time.sleep(measureTimeInterval)