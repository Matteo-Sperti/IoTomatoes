import time
import json
import random
import sys
from socket import gethostname, gethostbyname

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint
from ItemInfo import *

class IoTDevice(GenericEndpoint):
    def __init__(self, DeviceInfo : dict):
        super().__init__(DeviceInfo, isResource=True)

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
        message["e"]["value"] = random.randint(20,40)
        return message

    def get_humidity(self):
        message = self.construct_message("humidity", "%")
        message["e"]["value"] = random.randint(20,80)
        return message

    def get_light(self):
        message = self.construct_message("light", "lx") #1 lux = 1 lumen/m2
        message["e"]["value"] = random.randint(20,40)
        return message

    def get_soilMoisture(self):
        message = self.construct_message("soilMoisture", "%")
        message["e"]["value"] = random.randint(20,80)
        return message

if __name__ == "__main__":
    settings = json.load(open("DevicesSettings.json", "r"))
    ServiceCatalog_url = settings["ServiceCatalog_url"]
    measureTimeInterval = settings["measureTimeInterval"]
    NumberOfFieldsPerCompany = settings["NumberOfFieldsPerCompany"]
    NumberOfDevicesPerField = settings["NumberOfDevicesPerField"]

    Sensors = []
    for company in settings["Companies"]:
        for j in range(NumberOfFieldsPerCompany):
            for i in range(NumberOfDevicesPerField):
                IPport = 10000 + j*NumberOfDevicesPerField + i
                measures = random.sample(settings["MeasuresType"], random.randint(0, len(settings["MeasuresType"])))
                if len(measures) == 0:
                    isSensor = False
                else:
                    isSensor = True

                if random.randint(0, 1) == 0:
                    isActuator = False
                    actuators = []
                    PowerConsumption_kW = 0
                else:
                    isActuator = True
                    actuators = random.sample(settings["ActuatorsType"], 1)
                    PowerConsumption_kW = random.randint(5, 20)

                Device_information = {
                    "deviceName" : f"Device_{j*NumberOfDevicesPerField + i}",
                    "field" : j + 1,
                    "IPport" : IPport,
                    "IPaddress" : gethostbyname(gethostname()),
                    "isSensor" : isSensor,
                    "isActuator" : isActuator,
                    "measureType" : measures,
                    "actuatorType" : actuators,
                    "PowerConsumption_kW" : PowerConsumption_kW,
                    "CompanyName" : company["CompanyName"],
                    "CompanyToken" : company["CompanyToken"],
                    "ServiceCatalog_url" : ServiceCatalog_url
                }

                Sensors.append(IoTDevice(Device_information))
    
    try:
        for sensor in Sensors:
            sensor.start()

        while True:
            for sensor in Sensors:
                sensor.run()
                time.sleep(measureTimeInterval)
    except KeyboardInterrupt:
        for sensor in Sensors:
            sensor.stop()
