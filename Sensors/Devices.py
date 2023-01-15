import time
import json
import random
import sys
from socket import gethostname, gethostbyname

from IoTDevice import IoTDevice
sys.path.append("../SupportClasses/")
from MyIDGenerator import IDs
from TerminalQuery import *

HelpMessage = """
Devices Simulator.

Commands:
addDevices: populate a field
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

        self.Sensors = []

    def populateField(self, number : int = 5):
        CompanyName = input("Insert Company Name: ")
        CompanyToken = input("Insert Company Token: ")
        fieldNumber = query_int("Insert field number: ")

        for i in range(number):
            self.Sensors.append(self.createDevice(CompanyName, CompanyToken, fieldNumber))

    def createDevice(self, CompanyName : str, CompanyToken : str, fieldNumber : int):
        ID = self.DevicesIDs.get_ID()
        IPport = 10000 + ID
        if random.randint(0, 1) == 0:
            isActuator = False
            actuators = []
            PowerConsumption_kW = 0

            measures = random.sample(self._measuresType, random.randint(1, len(self._measuresType)))
            isSensor = True
        else:
            isActuator = True
            actuators = random.sample(self._actuatorsType, 1)
            PowerConsumption_kW = random.randint(5, 20)
            isSensor = False
            measures = []

        Device_information = {
            "deviceName" : f"Device_{ID}",
            "field" : fieldNumber,
            "IPport" : IPport,
            "IPaddress" : gethostbyname(gethostname()),
            "isSensor" : isSensor,
            "isActuator" : isActuator,
            "measureType" : measures,
            "actuatorType" : actuators,
            "PowerConsumption_kW" : PowerConsumption_kW,
            "CompanyName" : CompanyName,
            "CompanyToken" : CompanyToken,
            "ServiceCatalog_url" : self._ServiceCatalog_url
        }

        return IoTDevice(Device_information, self._measureTimeInterval)

    def getCompanyPosition(self, Companyinfo : dict):
        pass

    def stopDevice(self):
        pass

    def run(self) :
        print("\nType 'help' for the list of available commands")
        while True :
            command = input(">> ").lower()
            if command == "exit" :
                self.exit()
                return False
            elif command == "help" :
                print(HelpMessage)
                return True
            elif command == "adddevices" :
                self.populateField()
                return True
            elif command == "kill" :
                self.stopDevice()
                return True
            else :
                print("Command not found")
                return True
    
    def exit(self):
        for sensor in self.Sensors:
            sensor.stop()

if __name__ == "__main__":
    settings = json.load(open("DevicesSettings.json", "r"))

    Simulator = SimDevices_Manager(settings)

    print(HelpMessage)
    while True:
        run = Simulator.run()
        if not run :
            break   
    
    print("End of the simulator")