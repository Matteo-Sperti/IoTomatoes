import time
import sys

from AmbientSimulator import AmbientSimulator
sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint
from ItemInfo import *
from MyThread import MyThread

class IoTDevice(GenericEndpoint):
    def __init__(self, DeviceInfo : dict, Ambient : AmbientSimulator, measureTimeInterval : int = 3):
        super().__init__(DeviceInfo, isResource=True)
        self._Ambient = Ambient
        self._SendThread = MyThread(self.run, self.ID, measureTimeInterval)

        self._message={
            "companyName" : getCompanyName(self._CompanyInfo),
            "bn" : 0,
            "field" : getField(self._EndpointInfo),
            "e" : {
                "name": "",
                "value": None,
                "unit": "",       
                "timestamp": None
            }
        }

    def start(self):
        self._SendThread.start()
        self._Ambient.start()

    def close(self):
        self._SendThread.stop()

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")

    def run(self):
        for topic in publishedTopics(self._EndpointInfo):
            message = eval(f"self.get_{topic.split('/')[-1]}()")
            self.myPublish(topic, message)
    
    def construct_message(self, measure : str, unit : str) :
        message=self._message
        message["bn"]=self.ID
        message["e"]["name"] = measure
        message["e"]["value"] = 0
        message["e"]["timestamp"] = time.time()
        message["e"]["unit"] = unit
        return message

    def get_temperature(self):
        message = self.construct_message("temperature", "°C")
        message["e"]["value"] = self._Ambient.get_temperature()
        return message

    def get_humidity(self):
        message = self.construct_message("humidity", "%")
        message["e"]["value"] = self._Ambient.get_humidity()
        return message

    def get_light(self):
        message = self.construct_message("light", "lx") #1 lux = 1 lumen/m2
        message["e"]["value"] = self._Ambient.get_light()
        return message

    def get_soilMoisture(self):
        message = self.construct_message("soilMoisture", "%")
        message["e"]["value"] = self._Ambient.get_soilMoisture()
        return message