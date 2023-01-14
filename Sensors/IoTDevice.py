import time
import sys

from AmbientSimulator import AmbientSimulator
sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericResource
from ItemInfo import *
from MyThread import MyThread

class IoTDevice(GenericResource):
    def __init__(self, DeviceInfo : dict, Ambient : AmbientSimulator, measureTimeInterval : int = 3):
        super().__init__(DeviceInfo)
        self._Ambient = Ambient
        print("sono qui")
        self._message={
            "companyName" : getCompanyName(self._CompanyInfo),
            "bn" : 0,
            "field" : getField(self._EndpointInfo),
            "e" : [{
                "name": "",
                "value": None,
                "unit": "",       
                "timestamp": None
            }]
        }
        print(self._message)
        self._SendThread = MyThread(self.run, measureTimeInterval)

    def start(self):
        self.start()
        self._SendThread.start()

    def close(self):
        self._SendThread.stop()
        self.stop()

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")

    def run(self):
        for topic in publishedTopics(self._EndpointInfo):
            message = eval(f"self.get_{topic.split('/')[-1]}()")
            self.myPublish(self._baseTopic+topic, message)
    
    def construct_message(self, measure : str, unit : str) :
        message=self._message
        message["bn"]=self.ID
        message["e"][-1]["name"] = measure
        message["e"][-1]["value"] = 0
        message["e"][-1]["timestamp"] = time.time()
        message["e"][-1]["unit"] = unit
        return message

    def get_temperature(self):
        message = self.construct_message("temperature", "°C")
        message["e"][-1]["value"] = self._Ambient.get_temperature()
        return message

    def get_humidity(self):
        message = self.construct_message("humidity", "%")
        message["e"][-1]["value"] = self._Ambient.get_humidity()
        return message

    def get_light(self):
        message = self.construct_message("light", "lx") #1 lux = 1 lumen/m2
        message["e"][-1]["value"] = self._Ambient.get_light()
        return message

    def get_soilMoisture(self):
        message = self.construct_message("soilMoisture", "%")
        message["e"][-1]["value"] = self._Ambient.get_soilMoisture()
        return message