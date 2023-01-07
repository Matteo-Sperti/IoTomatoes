import time
import json
import random
import sys
from socket import gethostname, gethostbyname

from AmbientSimulator import AmbientSimulator
from IoTDevice import IoTDevice
sys.path.append("../SupportClasses/")
from MyIDGenerator import IDs

HelpMessage = """
Devices Simulator.
Commands:
help: print this help message
insert: insert a new device
kill: remove a device
exit: exit the program
"""

class SimDevices_Manager():
    def __init__(self, settings : dict):
        self._ServiceCatalog_url = settings["ServiceCatalog_url"]
        self._SystemToken = settings["SystemToken"]
        self._measureTimeInterval = settings["measureTimeInterval"]
        self._measuresType = settings["MeasuresType"]
        self._actuatorsType = settings["ActuatorsType"]
        self.DevicesIDs = IDs(1)

        self.Sensor = []

    def createDevice(self, field : int, device : int):
        ID = IDs.getNewID()
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

        field["DevicesList"].append(IoTDevice(Device_information, field["Ambient"], measureTimeInterval))



    def getPosition(self, field : int, device : int):
        pass

    def stopDevice(self, field : int, device : int):
        pass

if __name__ == "__main__":
    settings = json.load(open("DevicesSettings.json", "r"))

    Simulator = SimDevices_Manager(settings)

    print(HelpMessage)
    print("Press Ctrl+C to stop")
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
