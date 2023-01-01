import json
import time
import socket
from customExceptions import *

class Item():
    def __init__(self, ID : int = 0, IPport : int = 8080, availableServices : list = [], servicesDetails : list = []):
        self.info = {
            "ID" : ID,
            "availableServices": [],
            "servicesDetails": [],
            "lastUpdate": time.time()
        }

        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        self.info["availableServices"].append("REST")
        self.info["servicesDetails"].append({"serviceType" : "REST", "serviceIP": f"{local_ip}:{IPport}"})

        if len(availableServices) != len(servicesDetails):
            raise InfoException("Available services and details are different")

        for i in range(len(availableServices)):
            if availableServices[i] != "REST":
                self.addService(availableServices[i], servicesDetails[i])

    @property
    def ID(self) -> int:
        return self.info["ID"]

    @property
    def availableServices(self) -> list:
        return self.info["availableServices"]

    @property
    def servicesDetails(self) -> list:
        return self.info["servicesDetails"]

    @property
    def serviceIP(self) -> str:
        for service in self.info["servicesDetails"]:
            if service["serviceType"] == "REST":
                return service["serviceIP"]
        return ""

    @property
    def topic(self) -> str:
        for service in self.info["servicesDetails"]:
            if service["serviceType"] == "MQTT":
                return service["topic"]
        return ""

    @property
    def lastUpdate(self) -> float:
        return self.info["lastUpdate"]

    @ID.setter
    def ID(self, ID : int):
        self.info["ID"] = ID
        self.refresh()

    def addService(self, service : str, serviceInfo : dict = {}):
        self.info["availableServices"].append(service)
        if "serviceType" not in serviceInfo:
            serviceInfo["serviceType"] = service
        else:
            if serviceInfo["serviceType"] != service:
                raise Exception("Service type and service name are different")

        self.info["servicesDetails"].append(serviceInfo)
        self.refresh()

    def refresh(self):
        self.info["lastUpdate"] = time.time()

    def __dict__(self):
        return self.info

    def __str__(self) -> str:
        return json.dumps(self.info)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Item):
            if self.info["ID"] == __o.info["ID"]:
                return True
        return False

class ServiceInfo(Item):
    def __init__(self, serviceName : str, ID : int = 0, IPport : int = 8080, 
                    availableServices : list = [], servicesDetails : list = []):
        super().__init__(ID, IPport, availableServices, servicesDetails)
        self.info["serviceName"] = serviceName

    @property
    def serviceName(self) -> str:
        return self.info["serviceName"]
    
    @serviceName.setter
    def serviceName(self, serviceName : str):
        self.info["serviceName"] = serviceName
        self.refresh()

class Device(Item):
    def __init__(self, deviceName : str, companyName : str, ID : int = 0, IPport : int = 8080, isActuator : bool = False, 
                    isSensor : bool = False, measureType : list = [], actuators : list = [], PowerConsumption_kW : int = 0):
        super().__init__(ID, IPport)
        self.info["deviceName"] = deviceName
        self.info["companyName"] = companyName
        self.info["isActuator"] = isActuator
        self.info["isSensor"] = isSensor
        self.info["measureType"] = measureType
        self.info["actuators"] = actuators
        self.info["PowerConsumption_kW"] = PowerConsumption_kW

        MQTT_info = {
            "serviceType" : "MQTT", 
            "subscribedTopic": [],
            "publishedTopic": []}
        for measure in measureType:
            MQTT_info["publishedTopic"].append(f"{self.companyName}/{self.ID}/{measure}")
        for actuator in actuators:
            MQTT_info["subscribedTopic"].append(f"{self.companyName}/{self.ID}/{actuator}")

        self.addService("MQTT", MQTT_info)

    @property
    def deviceName(self) -> str:
        return self.info["deviceName"]

    @property
    def companyName(self) -> str:
        return self.info["companyName"]

    @property
    def isActuator(self) -> bool:
        return self.info["isActuator"]

    @property
    def isSensor(self) -> bool:
        return self.info["isSensor"]

    @property
    def measureType(self) -> list:
        return self.info["measureType"]

    @property
    def actuators(self) -> list:
        return self.info["actuators"]

    @property
    def PowerConsumption_kW(self) -> int:
        return self.info["PowerConsumption_kW"]

    @property
    def subscribedTopic(self) -> list:
        for service in self.info["servicesDetails"]:
            if service["serviceType"] == "MQTT":
                return service["subscribedTopic"]
        return []

    @property
    def publishedTopic(self) -> list:
        for service in self.info["servicesDetails"]:
            if service["serviceType"] == "MQTT":
                return service["publishedTopic"]
        return []

    @deviceName.setter
    def deviceName(self, deviceName : str):
        self.info["deviceName"] = deviceName
        self.refresh()
    
    @companyName.setter
    def companyName(self, companyName : str):
        self.info["companyName"] = companyName
        self.refresh()
    
    @isActuator.setter
    def isActuator(self, isActuator : bool, actuators : list = []):
        self.info["isActuator"] = isActuator

        if isActuator:
            self.info["actuators"] = actuators
            for service in self.info["servicesDetails"]:
                if service["serviceType"] == "MQTT":
                    service["subscribedTopic"] = []
                    for actuator in actuators:
                        service["subscribedTopic"].append(f"{self.companyName}/{self.ID}/{actuator}")
        else:
            self.info["actuators"] = []
            for service in self.info["servicesDetails"]:
                if service["serviceType"] == "MQTT":
                    service["subscribedTopic"] = []

        self.refresh()

    @PowerConsumption_kW.setter
    def PowerConsumption_kW(self, PowerConsumption_kW : int):
        self.info["PowerConsumption_kW"] = PowerConsumption_kW
        self.refresh()

    @isSensor.setter
    def isSensor(self, isSensor : bool, measureType : list = []):
        self.info["isSensor"] = isSensor

        if isSensor:
            self.info["measureType"] = measureType
            for service in self.info["servicesDetails"]:
                if service["serviceType"] == "MQTT":
                    service["publishedTopic"] = []
                    for measure in measureType:
                        service["publishedTopic"].append(f"{self.companyName}/{self.ID}/{measure}")
        else:
            self.info["measureType"] = []
            for service in self.info["servicesDetails"]:
                if service["serviceType"] == "MQTT":
                    service["publishedTopic"] = []

        self.refresh()

class Company():
    def __init__(self, name : str, ID : int = 0, adminID : int = 0):
        self.info = {
                    "ID": ID,
                    "name": name,
                    "adminID": adminID,
                }

class User():
    def __init__(self):
        self.info = {
            "Name": "Pino",
            "Surname" : "Daniele",
            "Company" : "Pino Srl",
            "TelegramID": 12313123123,
            "ServiceCatalog_url" : "http://localhost:8080/ServiceCatalog"
        }

