import time
import json
from AmbientSimulator import AmbientSimulator
from GenericEndpoint import GenericResource
from ItemInfo import *

class SimDevice(GenericResource):
    def __init__(self, DeviceInfo : dict):
        """Constructor of the simulated sensor. It will initialize the sensor and
        the MQTT client, it will register the sensor to the ResourceCatalog and to the broker
        and it will subscribe to the topics specified in the ResourceCatalog.
        
        Finally it start the simulator of the ambient conditions."""

        super().__init__(DeviceInfo)
        self._Ambient = AmbientSimulator()
        self._message={
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

    def notify(self, topic, msg):
        print(f"Resource {self.ID} received message on topic {topic}\n")

        if self.isActuator:
            actuator_info = actuatorType(self._EndpointInfo)
            actuator_topic = topic.split("/")[-1]

            if actuator_topic in actuator_info:
                try:
                    state = msg["e"][0]["v"]
                except KeyError:
                    print("Message not valid")
                else:
                    if state == 0:
                        print(f"Resource {self.ID}: {actuator_topic} turned OFF")
                        self._Ambient.setActuator(actuator_topic, False)
                    elif state == 1:
                        print(f"Resource {self.ID}: {actuator_topic} turned ON")
                        self._Ambient.setActuator(actuator_topic, True)
                    else:
                        print(f"Resource {self.ID}: {actuator_topic} state not valid")
            else:
                print(f"Resource {self.ID}: {actuator_topic} not found")
            
    def get_measures(self):
        """This function is called periodically in order to get the sensor readings.
        It will publish the readings on the topics specified in the ResourceCatalog.
        
        It performs the same task as the get_measures function of the real sensor."""

        for topic in publishedTopics(self._EndpointInfo):
            message = eval(f"self.get_{topic.split('/')[-1]}()")
            self.myPublish(topic, message)
    
    def construct_message(self, measure : str, unit : str) :
        """This function is used to construct the message to be published on the topics."""

        message=self._message.copy()
        message["bn"]=self.ID
        message["e"][-1]["n"] = measure
        message["e"][-1]["v"] = 0
        message["e"][-1]["t"] = time.time()
        message["e"][-1]["u"] = unit
        return message

    def get_temperature(self):
        """This function is used to get the temperature reading from the AmbientSimulator."""

        message = self.construct_message("temperature", "C")
        message["e"][-1]["v"] = self._Ambient.get_temperature()
        return message

    def get_humidity(self):
        """This function is used to get the humidity reading from the AmbientSimulator."""

        message = self.construct_message("humidity", "%")
        message["e"][-1]["v"] = self._Ambient.get_humidity()
        return message

    def get_light(self):
        """This function is used to get the light reading from the AmbientSimulator."""

        message = self.construct_message("light", "lx") #1 lux = 1 lumen/m2
        message["e"][-1]["v"] = self._Ambient.get_light()
        return message

    def get_soilMoisture(self):
        """This function is used to get the soil moisture reading from the AmbientSimulator."""
        
        message = self.construct_message("soilMoisture", "%")
        message["e"][-1]["v"] = self._Ambient.get_soilMoisture()
        return message

if __name__ == "__main__":
    try:
        settings = json.load(open("DeviceSettings.json"))
        IoTSensor = SimDevice(settings)

        measureTimeInterval = settings["measureTimeInterval"]
    except Exception as e:
        print(e)
    else:
        while True:
            IoTSensor.get_measures()
            time.sleep(measureTimeInterval)