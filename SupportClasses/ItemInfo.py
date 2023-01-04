import json
import time
import socket

from MyExceptions import InfoException

class EndpointInfo():
    def __init__(self, dict : dict = {}, isService : bool = False, isResource : bool = False):
        if dict != {}:
            self.info = dict
        else:
            self.info = {
                "availableServices": list(),
                "servicesDetails": list(),
            }
        if self._isService ^ self._isResource:
            raise InfoException("The Endpoint must be a service or a resource, not both or none")
        else:
            self._isService = isService
            self._isResource = isResource
        self.CompanyInfo = {}

    def constructService(self, ID : int, EInfo : dict):
        if "serviceName" not in EInfo:
            raise InfoException("Service name is missing")
        self.info["serviceName"] = EInfo["serviceName"]

        if "availableServices" in EInfo:
            if len(EInfo["availableServices"]) != len(EInfo["servicesDetails"]):
                raise InfoException("Available services and details are different")
            for i in range(len(EInfo["availableServices"])):
                if EInfo["availableServices"][i] in ["REST", "MQTT"]:
                    self.addService(EInfo["availableServices"][i], EInfo["servicesDetails"][i])
                else:
                    raise InfoException("Service not supported")
                self.info["servicesDetails"] = EInfo["servicesDetails"]

        if "IPport" in EInfo and "IPaddress" in EInfo:
            self.setIPport(EInfo["IPaddress"], EInfo["IPport"])
        
        return self.info

    def constructResource(self, ID : int, EInfo : dict):
        pass

    def construct(self, EInfo : dict, CompInfo : dict = {}):
        self.info["availableServices"].append("REST")
        self.info["servicesDetails"].append({"serviceType" : "REST"})
        self.setIPport(EInfo["IPport"])

        if len(EInfo["availableServices"]) != len(EInfo["servicesDetails"]):
            raise InfoException("Available services and details are different")

        for i in range(len(EInfo["availableServices"])):
            if EInfo["availableServices"][i] != "REST":
                self.addService(EInfo["availableServices"][i], EInfo["servicesDetails"][i])

        if self._isService:
            self.info["serviceName"] = EInfo["serviceName"]
        else:
            if "CompanyName" in CompInfo and "CompanyToken" in CompInfo:
                self.CompanyInfo["CompanyName"] = CompInfo["CompanyName"]
                self.CompanyInfo["CompanyToken"] = CompInfo["CompanyToken"],
            else:
                raise InfoException("CompanyInfo is not valid")

            self.info["deviceName"] = EInfo["deviceName"]
            self.info["field"] = EInfo["fieldID"]
            self.info["isActuator"] = EInfo["isActuator"]
            self.info["isSensor"] = EInfo["isSensor"]
            self.info["measureType"] = EInfo["measureType"]
            self.info["actuators"] = EInfo["actuators"]
            self.info["PowerConsumption_kW"] = EInfo["PowerConsumption_kW"]

            MQTT_info = {
                "serviceType" : "MQTT", 
                "subscribedTopic": [],
                "publishedTopic": []}
            for measure in self.measureType:
                MQTT_info["publishedTopic"].append(f"{self.companyName}/{self.field}/{self.ID}/{measure}")
            for actuator in self.actuators:
                MQTT_info["subscribedTopic"].append(f"{self.companyName}/{self.field}/{self.ID}/{actuator}")

            self.addService("MQTT", MQTT_info)

        return self.info, self.CompanyInfo

    def setIPport(self, local_ip : str,  IPport : int):
        service = {
            "serviceType" : "REST",
            "serviceIP" : f"http://{local_ip}:{IPport}" }
        self.info["servicesDetails"].append(service)
        self.info["availableServices"].append("REST")

    def addService(self, service : str, serviceInfo : dict = {}):
        self.info["availableServices"].append(service)
        if "serviceType" not in serviceInfo:
            serviceInfo["serviceType"] = service
        else:
            if serviceInfo["serviceType"] != service:
                raise InfoException("Service type and service name are different")

        self.info["servicesDetails"].append(serviceInfo)

    def setActuator(self, isActuator : bool, actuators : list = []):
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

    def setSensor(self, isSensor : bool, measureType : list):
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

    @property
    def companyName(self) -> str:
        return self.info["companyName"]

    @property
    def field(self) -> int:
        return self.info["field"]

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
    def isMQTT(self) -> bool:
        for service in self.info["availableServices"]:
            if service == "MQTT":
                return True
        return False

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

    @property
    def IPaddress(self) -> str:
        for service in self.info["servicesDetails"]:
            if service["serviceType"] == "REST":
                return service["serviceIP"]
        return ""