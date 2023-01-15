import time
import sys

from AmbientSimulator import AmbientSimulator
sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericResource
from ItemInfo import *
from MyThread import MyThread

class IoTDevice(GenericResource):
    def __init__(self, DeviceInfo : dict, measureTimeInterval : int = 3):
        super().__init__(DeviceInfo)
        self._Ambient = AmbientSimulator(getCompanyName(self._CompanyInfo), getField(self._EndpointInfo))
        self._message={
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
            self.myPublish(topic, message)
    
    def construct_message(self, measure : str, unit : str) :
        message=self._message
        message["bn"]=self.ID
        message["e"][-1]["n"] = measure
        message["e"][-1]["v"] = 0
        message["e"][-1]["t"] = time.time()
        message["e"][-1]["u"] = unit
        return message

    def get_temperature(self):
        message = self.construct_message("temperature", "°C")
        message["e"][-1]["v"] = self._Ambient.get_temperature()
        return message

    def get_humidity(self):
        message = self.construct_message("humidity", "%")
        message["e"][-1]["v"] = self._Ambient.get_humidity()
        return message

    def get_light(self):
        message = self.construct_message("light", "lx") #1 lux = 1 lumen/m2
        message["e"][-1]["v"] = self._Ambient.get_light()
        return message

    def get_soilMoisture(self):
        message = self.construct_message("soilMoisture", "%")
        message["e"][-1]["v"] = self._Ambient.get_soilMoisture()
        return message