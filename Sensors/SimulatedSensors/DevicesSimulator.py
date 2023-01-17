import time
import json
import random
import requests
import sys

from FakeSensor import SimDevice
sys.path.append("../../SupportClasses/")
from MyIDGenerator import IDs
from TerminalQuery import *
from MyThread import MyThread

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
        self._measuresType = settings["MeasuresType"]
        self._actuatorsType = settings["ActuatorsType"]
        self.DevicesIDs = IDs(1)

        self.Sensors = []
        self._ResourceCatalog_url = self.get_ResourceCatalog_url()
        self._measureThread = MyThread(self.measure, settings["measureTimeInterval"])

    def measure(self):
        for sensor in self.Sensors:
            sensor.get_measures()

    def populateField(self, number : int = 5):
        CompanyName = input("Insert Company Name: ")
        CompanyToken = input("Insert Company Token: ")
        fieldNumber = query_int("Insert field number: ")

        CompanyInfo = {
            "CompanyName" : CompanyName,
            "CompanyToken" : CompanyToken
        }
        latitude, longitude = self.getCompanyPosition(CompanyInfo)
        for i in range(number):
            self.Sensors.append(self.createDevice(CompanyInfo, fieldNumber, latitude, longitude))

    def createDevice(self, CompanyInfo : dict, fieldNumber : int, latitude : float, longitude : float):
        ID = self.DevicesIDs.get_ID()

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
            "deviceName" : f"SimDevice_{ID}",
            "field" : fieldNumber,
            "isSensor" : isSensor,
            "isActuator" : isActuator,
            "measureType" : measures,
            "actuatorType" : actuators,
            "PowerConsumption_kW" : PowerConsumption_kW,
            "CompanyName" : CompanyInfo["CompanyName"],
            "CompanyToken" : CompanyInfo["CompanyToken"],
            "ServiceCatalog_url" : self._ServiceCatalog_url
        }
        
        dev_latitude, dev_longitude = self.generatePosition(latitude, longitude, fieldNumber)
        if dev_latitude != -1 and dev_longitude != -1:
            Device_information["Location"] = {
                "latitude" : dev_latitude,
                "longitude" : dev_longitude
            }
        return SimDevice(Device_information)

    def get_ResourceCatalog_url(self) :
        """Get the URL of the Resource Catalog from the Service Catalog."""

        while True:
            try:
                params = {"SystemToken": self._SystemToken}
                res = requests.get(self._ServiceCatalog_url + "/ResourceCatalog_url", params = params)
                res.raise_for_status()
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    res_dict = res.json()
                    return res_dict["ResourceCatalog_url"]
                except:
                    print(f"Error in the Resource information\nRetrying connection\n")
                    time.sleep(1)

    def getCompanyPosition(self, Companyinfo : dict):
        try:
            response = requests.get(f"{self._ResourceCatalog_url}/location", params = Companyinfo)
            response.raise_for_status()
            r_dict = response.json()["Location"]
            latitude = r_dict["latitude"]
            longitude = r_dict["longitude"]
        except:
            print("Error in the Resource Catalog")
            return -1, -1
        else:
            return latitude, longitude

    def generatePosition(self, latitude : float, longitude : float, fieldNumber : int):
        """Generate a random position inside a field"""
        if fieldNumber == 1:
            dev_latitude = latitude + random.uniform(0, 0.005)
            dev_longitude = longitude + random.uniform(0, 0.005)
        elif fieldNumber == 2:
            dev_latitude = latitude + random.uniform(0, 0.005)
            dev_longitude = longitude - random.uniform(0, 0.005)
        elif fieldNumber == 3:
            dev_latitude = latitude - random.uniform(0, 0.005)
            dev_longitude = longitude + random.uniform(0, 0.005)
        elif fieldNumber == 4:
            dev_latitude = latitude - random.uniform(0, 0.005)
            dev_longitude = longitude - random.uniform(0, 0.005)
        else:
            dev_latitude = latitude + random.uniform(0.005, 0.01)
            dev_longitude = longitude + random.uniform(0, 0.01)

        return dev_latitude, dev_longitude

    def stopDevice(self):
        companyName = input("Insert Company Name: ")
        field = query_int("Insert field number: ")

        for sensor in self.Sensors:
            if sensor.CompanyName == companyName and sensor.field == field:
                sensor.stop()
                print(sensor)
                self.Sensors.remove(sensor)
                return

        print("No device found with the given information")

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
        self._measureThread.stop()
        for sensor in self.Sensors:
            sensor.stop()

if __name__ == "__main__":
    settings = json.load(open("DevicesSimulatorSettings.json", "r"))

    Simulator = SimDevices_Manager(settings)

    print(HelpMessage)
    while True:
        run = Simulator.run()
        if not run :
            break   
    
    print("End of the simulator")