import json
import random
import requests

from FakeDevice import SimDevice
import sys
sys.path.append("../../IoTomatoes_SupportPackage/src/")
from iotomatoes_supportpackage.MyIDGenerator import IDs

HelpMessage = """
Devices Simulator.

Commands:
addDevices: populate a field
kill: remove a device
exit: exit the program
"""

class SimDevices_Manager():
    def __init__(self, settings : dict):
        self._platform_url = settings["IoTomatoes_url"]
        self._measuresType = settings["MeasuresType"]
        self._actuatorsType = settings["ActuatorsType"]
        self.DevicesIDs = IDs(1)

        self.Sensors = []

    def populateField(self, number : int = 5):
        CompanyName = input("Insert Company Name: ")
        fieldNumber = query_int("Insert field number: ")

        latitude, longitude = self.getCompanyPosition(CompanyName)
        for i in range(number):
            self.Sensors.append(self.createDevice(CompanyName, fieldNumber, latitude, longitude))

    def createDevice(self, CompanyName : str, fieldNumber : int, latitude : float, longitude : float):
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
            "CompanyName" : CompanyName,
            "IoTomatoes_url" : self._platform_url
        }
        
        dev_latitude, dev_longitude = self.generatePosition(latitude, longitude, fieldNumber)
        if dev_latitude != -1 and dev_longitude != -1:
            Device_information["Location"] = {
                "latitude" : dev_latitude,
                "longitude" : dev_longitude
            }
        return SimDevice(Device_information)

    def getCompanyPosition(self, CompanyName : str):
        try:
            response = requests.get(f"{self._platform_url}/rc/{CompanyName}/location")
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
        CompanyName = input("Insert Company Name: ")
        field = query_int("Insert field number: ")

        for sensor in self.Sensors:
            if sensor.CompanyName == CompanyName and sensor.field == field:
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
        for sensor in self.Sensors:
            sensor.close()

def query_int(question):
    """Ask a question via input() and return the int answer"""
    while True:
        resp = input(question)
        if _is_integer(resp):
            return int(resp)
        else:
            print(f"Please respond with a integer number\n")

def _is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

if __name__ == "__main__":
    settings = json.load(open("DevicesSimulatorSettings.json", "r"))

    Simulator = SimDevices_Manager(settings)

    print(HelpMessage)
    while True:
        run = Simulator.run()
        if not run :
            break   
    
    print("End of the simulator")