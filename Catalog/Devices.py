import time
import random
from GenericEndPoints import GenericMQTTResource
from ItemInfo import Device

MeasuresType = ["temperature", "humidity", "pressure", "light", "soilMoisture"]
ActuatorsType = ["led", "pump"]
NumberOfDevices = 10
measureTimeInterval = 3

class IoTDevice(GenericMQTTResource):
    def __init__(self, DeviceInfo : Device, ServiceCatalog_url: str):
        super().__init__(DeviceInfo, ServiceCatalog_url)
        self.client.start()
        for topic in self.info.subscribedTopics:
            self.client.mySubscribe(self.baseTopic + "/" + topic)

    def notify(self, topic, msg):
        print(f"{self.ID} received {msg} on topic {topic}")

    def run(self):
        for topic in self.info.publishedTopics:
            self.publish(topic, eval(f"self.get_{topic.lower()}()"))

    def stop(self):
        self.client.stop()
        self.Thread.close()

    def publish(self, topic, msg):
        self.client.myPublish(self.baseTopic + "/" + topic, msg)

    def get_temperature(self):
        return 18

    def get_humidity(self):
        return 50

    def get_pressure(self):
        return 1000

    def get_light(self):
        return 100

    def get_soilMoisture(self):
        return 10

if __name__ == "__main__":
    Sensors = []
    ServiceCatalog_url = "http://localhost:8080/ServiceCatalog"
    CompanyName = "MagicFarm S.r.l."
    for i in range(NumberOfDevices):
        IPport = 10000 + i
        measures = random.sample(MeasuresType, random.randint(0, len(MeasuresType)))
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
            actuators = random.sample(ActuatorsType, 1)
            PowerConsumption_kW = random.randint(5, 20)

        DeviceInfo = Device(f"Device{i}", CompanyName, 0, IPport, isActuator, isSensor, measures, actuators, PowerConsumption_kW)

        Sensors.append(IoTDevice(DeviceInfo, ServiceCatalog_url))
    
    try:
        while True:
            for sensor in Sensors:
                sensor.run()
                time.sleep(measureTimeInterval)
    except KeyboardInterrupt:
        for sensor in Sensors:
            sensor.stop()


