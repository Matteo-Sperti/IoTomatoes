import time
import json
import random
from GenericEndPoints import GenericMQTTResource
from ItemInfo import DeviceInfo

class IoTDevice(GenericMQTTResource):
    def __init__(self, DeviceInfo : DeviceInfo, ServiceCatalog_url: str):
        super().__init__(DeviceInfo, ServiceCatalog_url, isDevice=True)
        self.client.start()
        for topic in self.info.subscribedTopics:
            self.client.mySubscribe(self.baseTopic + "/" + topic)

        self.message={
            "companyName":self.info.companyName,
            "bn":self.ID,
            "field":self.info.field,
            "e": {
                "name": "",
                "value": None,
                "unit": "",       
                "timestamp": None
            }
        }

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")

    def run(self):
        for topic in self.info.publishedTopics:
            self.publish(topic, eval(f"self.get_{topic.lower()}()"))
            
    def publish(self, topic, msg):
        self.client.myPublish(self.baseTopic + "/" + topic, msg)

    def get_temperature(self):
        message=self.message
        message["e"]["name"]="temperature"
        message["e"]["value"]=random.randint(20,40)
        message["e"]["timestamp"]=time.time()
        message["e"]["unit"]="°C"
        return message

    def get_humidity(self):
        message=self.message
        message["e"]["name"] = "humidity"
        message["e"]["value"] = random.randint(20,80)
        message["e"]["timestamp"] = time.time()
        message["e"]["unit"] = "%"
        return message

    def get_light(self):
        message=self.message
        message["e"]["name"] = "light"
        message["e"]["value"] = random.randint(20,40)
        message["e"]["timestamp"] = time.time()
        message["e"]["unit"] = "lx"       #1 lux = 1 lumen/m2
        return message


    def get_soilMoisture(self):
        message=self.message
        message["e"]["name"] = "soilMoisture"
        message["e"]["value"] = random.randint(45,70)
        message["e"]["timestamp"] = time.time()
        message["e"]["unit"] = "%"
        return message

if __name__ == "__main__":
    settings = json.load(open("settings.json", "r"))
    ServiceCatalog_url = settings["ServiceCatalog_url"]
    measureTypeInterval = settings["measureTimeInterval"]
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

                Device_information = DeviceInfo(f"Device{i}", company, j, 0, IPport, isActuator, isSensor, measures, actuators, PowerConsumption_kW)

                Sensors.append(IoTDevice(Device_information, ServiceCatalog_url))
    
    try:
        while True:
            for sensor in Sensors:
                sensor.run()
                time.sleep(measureTypeInterval)
    except KeyboardInterrupt:
        for sensor in Sensors:
            sensor.stop()
