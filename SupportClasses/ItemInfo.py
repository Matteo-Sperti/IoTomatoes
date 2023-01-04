import time

from MyExceptions import InfoException

def getID(self) -> int:
    if "ID" not in self.info:
        raise InfoException("ID is missing")   
    else:
        return self.info["ID"]

def getCompanyName(dict : dict) -> str:
    if "CompanyName" not in dict:
        raise InfoException("Company name is missing")
    else:
        return dict["CompanyName"]

def getField(dict : dict) -> int:
    return dict["field"]

def isActuator(dict : dict) -> bool:
    if "isActuator" not in dict:
        raise InfoException("isActuator is missing")
    else:
        return dict["isActuator"]

def isSensor(dict : dict) -> bool:
    if "isSensor" not in dict:
        raise InfoException("isSensor is missing")
    else:
        return dict["isSensor"]

def measureType(dict : dict) -> list:
    return dict["measureType"]

def actuators(dict : dict) -> list:
    return dict["actuators"]

def PowerConsumption_kW(dict : dict) -> int:
    return dict["PowerConsumption_kW"]

def isMQTT(dict : dict) -> bool:
    for service in dict["availableServices"]:
        if service == "MQTT":
            return True
    return False

def subscribedTopics(dict : dict) -> list:
    for service in dict["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["subscribedTopic"]
    return []

def publishedTopics(dict : dict) -> list:
    for service in dict["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["publishedTopic"]
    return []

def getIPaddress(dict : dict) -> str:
    for service in dict["servicesDetails"]:
        if service["serviceType"] == "REST":
            return service["serviceIP"]
    return ""

def construct(EInfo : dict, CompInfo : dict = {}, isService : bool = False, isResource : bool = False):
    if isResource ^ isService:
        raise InfoException("isResource and isService are not compatible")
    if isService:
        info = _makeService(EInfo)
        CompanyInfo = {}
    else:
        if "CompanyName" not in CompInfo and "CompanyToken" not in CompInfo:
            raise InfoException("Company name is missing")
        else:
            CompanyInfo = {
                "CompanyName" : CompInfo["CompanyName"],
                "CompanyToken" : CompInfo["CompanyToken"]
            }
        info = _makeResource(EInfo, CompInfo)
    return info, CompanyInfo

def constructService(self, ID : int, EInfo : dict):
    self.info["ID"] = ID
    self.info["lastUpdate"] = time.time()
    self._makeService(EInfo)
    return self.info

def constructResource(ID : int, CompInfo : dict, EInfo : dict):
    info = {}
    info["ID"] = ID
    info["lastUpdate"] = time.time()

    info = _makeResource(EInfo, CompInfo, info)
    return info

def _makeService(EInfo : dict):
    info = {}
    if "serviceName" not in EInfo:
        raise InfoException("Service name is missing")
    info["serviceName"] = EInfo["serviceName"]

    if "availableServices" in EInfo:
        if len(EInfo["availableServices"]) != len(EInfo["servicesDetails"]):
            raise InfoException("Available services and details are different")
        for i in range(len(EInfo["availableServices"])):
            if EInfo["availableServices"][i] in ["REST", "MQTT"]:
                _addService(info, EInfo["availableServices"][i], EInfo["servicesDetails"][i])
            else:
                raise InfoException("Service not supported")
            info["servicesDetails"] = EInfo["servicesDetails"]

    if "IPport" in EInfo and "IPaddress" in EInfo:
        _setIPport(info, EInfo["IPaddress"], EInfo["IPport"])
    
    return info

def _makeResource(EInfo : dict, CompInfo : dict, info : dict = {}):
    if "ID" not in info:
        raise InfoException("ID is missing")
    if "CompanyName" not in CompInfo:
        raise InfoException("Company name is missing")

    if "deviceName" not in EInfo:
        raise InfoException("Device name is missing")
    else:
        info["deviceName"] = EInfo["deviceName"]
    
    if "field" in EInfo:
        info["field"] = EInfo["field"]
    else: 
        info["field"] = 1

    MQTT_info = {
                "serviceType" : "MQTT", 
                "subscribedTopic": [],
                "publishedTopic": []
                }

    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuator" not in EInfo:
            raise InfoException("Actuators names is missing")
        info["isActuator"] = True
        info["actuator"] = EInfo["actuators"]
        for actuator in EInfo["actuators"]:
            MQTT_info["subscribedTopic"].append(f"{CompInfo['CompanyName']}/{info['field']}/{info['ID']}/{actuator}")
    else:
        info["isActuator"] = False
        info["actuator"] = []

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        info["isSensor"] = True
        info["measureType"] = EInfo["measureType"]
        for measure in EInfo["measureType"]:
            MQTT_info["publishedTopic"].append(f"{CompInfo['CompanyName']}/{info['field']}/{info['ID']}/{measure}")
    else:
        info["isSensor"] = False
        info["measureType"] = []
    
    if "PowerConsumption_kW" in EInfo:
        info["PowerConsumption_kW"] = EInfo["PowerConsumption_kW"]
    else:
        info["PowerConsumption_kW"] = 0

    _addService(info, "MQTT", MQTT_info)

    return info

def _setIPport(dict : dict, local_ip : str,  IPport : int):
    service = {
        "serviceType" : "REST",
        "serviceIP" : f"http://{local_ip}:{IPport}" }
    dict["servicesDetails"].append(service)
    dict["availableServices"].append("REST")

def _addService(dict : dict, service : str, serviceInfo : dict = {}):
    dict["availableServices"].append(service)
    if "serviceType" not in serviceInfo:
        serviceInfo["serviceType"] = service
    else:
        if serviceInfo["serviceType"] != service:
            raise InfoException("Service type and service name are different")

    dict["servicesDetails"].append(serviceInfo)