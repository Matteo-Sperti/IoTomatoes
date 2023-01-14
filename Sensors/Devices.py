import time
import json
import random
import sys
from socket import gethostname, gethostbyname

from AmbientSimulator import AmbientSimulator
from IoTDevice import IoTDevice
sys.path.append("../SupportClasses/")
from MyIDGenerator import IDs
from TerminalQuery import *

HelpMessage = """
Devices Simulator.

Commands:
insertCompany: insert a company
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

        self.FieldsList = []

    def insertCompany(self):
        companyName = input("Insert Company Name: ")
        companyToken = input("Insert Company Token: ")
        numberOfFields = query_int("Insert number of fields: ")
        for i in range(numberOfFields):
            field = {
                "CompanyName" : companyName,
                "CompanyToken" : companyToken,
                "field" : i+1,
                "Ambient" : AmbientSimulator(companyName, i+1),
                "DevicesList" : []
            }
            self.FieldsList.append(field)

    def populateField(self, number : int = 10):
        CompanyName = input("Insert Company Name: ")
        fieldNumber = query_int("Insert field number: ")

        field = self.getField(CompanyName, fieldNumber)
        if field == None:
            print("Field not found")
            return

        for i in range(number):
            field["DevicesList"].append(self.createDevice(field))

    def getField(self, CompanyName : str, fieldNumber : int):
        for field in self.FieldsList:
            if field["CompanyName"] == CompanyName and field["field"] == fieldNumber:
                return field
        return None

    def createDevice(self, field : dict):
        ID = self.DevicesIDs.get_ID()
        IPport = 10000 + ID
        measures = random.sample(self._measuresType, random.randint(0, len(self._measuresType)))
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
            actuators = random.sample(self._actuatorsType, 1)
            PowerConsumption_kW = random.randint(5, 20)

        Device_information = {
            "deviceName" : f"Device_{ID}",
            "field" : field["field"],
            "IPport" : IPport,
            "IPaddress" : gethostbyname(gethostname()),
            "isSensor" : isSensor,
            "isActuator" : isActuator,
            "measureType" : measures,
            "actuatorType" : actuators,
            "PowerConsumption_kW" : PowerConsumption_kW,
            "CompanyName" : field["CompanyName"],
            "CompanyToken" : field["CompanyToken"],
            "ServiceCatalog_url" : self._ServiceCatalog_url
        }

        return IoTDevice(Device_information, field["Ambient"], self._measureTimeInterval)

    def getCompanyPosition(self, Companyinfo : dict):
        pass

    def stopDevice(self):
        CompanyName = input("Insert Company Name: ")
        fieldNumber = query_int("Insert field number: ")
        
        field = self.getField(CompanyName, fieldNumber)
        if field == None:
            print("Field not found")
            return

        sensor = field.pop("DevicesList")
        sensor.stop()
        print("Device stopped\n")
        print(json.dumps(sensor._EndpointInfo, indent=4))

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
            elif command == "insertcompany" :
                self.insertCompany()
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
        for field in self.FieldsList:
            for device in field["DevicesList"]:
                device.stop()

if __name__ == "__main__":
    settings = json.load(open("DevicesSettings.json", "r"))

    Simulator = SimDevices_Manager(settings)

    print(HelpMessage)
    while True:
        run = Simulator.run()
        if not run :
            break   
    
    print("End of the simulator")