import time

from iotomatoes_supportpackage.MyExceptions import InfoException

### Get item information from a dictionary ###

def measureType(dict_ : dict) -> list:
    if "measureType" not in dict_:
        raise InfoException("measureType is missing")
    else:
        return dict_["measureType"]

def actuatorType(dict_ : dict) -> list:
    if "actuatorType" not in dict_:
        raise InfoException("actuatorType is missing")
    else:
        return dict_["actuatorType"]

def PowerConsumption_kW(dict_ : dict) -> int:
    if "PowerConsumption_kW" not in dict_:
        raise InfoException("PowerConsumption_kW is missing")
    else:
        return dict_["PowerConsumption_kW"]

def isMQTT(dict_ : dict) -> bool:
    if "availableServices" not in dict_:
        return False
    
    for service in dict_["availableServices"]:
        if service == "MQTT":
            return True
    return False

def subscribedTopics(dict_ : dict) -> list:
    if "servicesDetails" not in dict_:
        return []
    
    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["subscribedTopics"]
    return []

def publishedTopics(dict_ : dict) -> list:
    if "servicesDetails" not in dict_:
        return []
    
    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["publishedTopics"]
    return []

def getIPaddress(dict_ : dict) -> str:
    if "servicesDetails" not in dict_:
        return ""
    
    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "REST":
            return service["serviceIP"]
    return ""

### Construct item dictionary according to the specification of the catalog ###
def constructService(ID : int, EInfo : dict):
    """ Construct the dictionary of a service according to the specification of the catalog.

    Arguments:\n
    `ID (int)`: The ID of the service.\n
    `EInfo (dict)`: The dictionary containing the information of the service.\n

    Returns:\n
    `info` (dict)`: The dictionary of the service.\n
    """
    info = {}
    info["ID"] = ID
    _makeService(info, EInfo)
    info["lastUpdate"] = time.time()
    return info

def constructResource(ID : int, CompName : str, EInfo : dict):
    """ Construct the dictionary of a resource according to the specification of the catalog.

    Arguments:\n
    `ID (int)`: The ID of the resource.\n
    `CompName (str)`: The name of the company of the resource.\n
    `EInfo (dict)`: The dictionary containing the information of the resource.\n

    Returns:\n
    `info (dict)`: The dictionary of the resource.\n
    """
    info = {}
    info["ID"] = ID
    _makeResource(info, EInfo)
    _makeResourceTopic(info, EInfo, CompName)
    info["lastUpdate"] = time.time()
    return info

def _makeResourceTopic(dict_to_construct: dict, EInfo : dict, CompanyName : str):
    """If the resource is a sensor or an actuator, add the MQTT topics to the dictionary.
    
    Arguments:\n
    `dict_to_construct (dict)`: The dictionary of the resource.\n
    `EInfo (dict)`: The dictionary containing the information of the resource.\n
    `CompInfo (dict)`: The dictionary containing the information of the company of the resource.\n    
    """

    if "ID" not in dict_to_construct:
        raise InfoException("ID is missing")

    subscribedTopics = []
    publishedTopics = []

    BaseTopic = CompanyName.replace(" ", "_")
    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuatorType" not in EInfo:
            raise InfoException("Actuators names is missing")
        for actuator in EInfo["actuatorType"]:
            subscribedTopics.append(f"{BaseTopic}/{EInfo['field']}/{dict_to_construct['ID']}/{actuator}")

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        for measure in EInfo["measureType"]:
            publishedTopics.append(f"{BaseTopic}/{EInfo['field']}/{dict_to_construct['ID']}/{measure}")

    _addMQTT(dict_to_construct, subscribedTopics=subscribedTopics, publishedTopics=publishedTopics)


def _makeResource(info : dict, EInfo : dict):
    """Construct the dictionary of a resource according to the specification of the catalog."""

    info["availableServices"] = []
    info["servicesDetails"] = []

    if "deviceName" not in EInfo:
        raise InfoException("Device name is missing")
    else:
        info["deviceName"] = EInfo["deviceName"]
    
    if "field" in EInfo:
        info["field"] = EInfo["field"]
    else: 
        info["field"] = 1 

    if "latitude" in EInfo and "longitude" in EInfo:
        info["Location"] = {
            "latitude" : EInfo["latitude"],
            "longitude" : EInfo["longitude"]
        }
    elif "Location" in EInfo and "latitude" in EInfo["Location"] and "longitude" in EInfo["Location"]:
        info["Location"] = EInfo["Location"]
    else:
        info["Location"] = {
            "latitude" : -1,
            "longitude" : -1
        }
    
    if "PowerConsumption_kW" in EInfo:
        info["PowerConsumption_kW"] = EInfo["PowerConsumption_kW"]
    else:
        info["PowerConsumption_kW"] = 0

    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuatorType" not in EInfo:
            raise InfoException("Actuators names is missing")
        info["isActuator"] = True
        info["actuatorType"] = EInfo["actuatorType"]
    else:
        info["isActuator"] = False
        info["actuatorType"] = []

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        info["isSensor"] = True
        info["measureType"] = EInfo["measureType"]
    else:
        info["isSensor"] = False
        info["measureType"] = []


def _makeService(EInfo : dict, info : dict = {}):
    if "serviceName" not in EInfo:
        raise InfoException("Service name is missing")
    info["serviceName"] = EInfo["serviceName"]

    info["availableServices"] = []
    info["servicesDetails"] = []

    if "availableServices" in EInfo:
        if "MQTT" in EInfo["availableServices"]:
            _addMQTT(info, **EInfo)
        if "REST" in EInfo["availableServices"]:
            _addREST(info, **EInfo)
        

    if "IPaddress" in EInfo:
        _addREST(info, **EInfo)
    
    return info.copy()

def _addREST(dict_ : dict, **kwargs):
    """Add the REST service information to the dictionary."""
    
    local_ip = kwargs["IPaddress"]

    if "IPport" in kwargs:
        IPport = kwargs["IPport"]
    else:
        IPport = 8080

    service = {
        "serviceType" : "REST",
        "serviceIP" : ""
    }
    service = {
        "serviceType" : "REST",
        "serviceIP" : f"http://{local_ip}:{IPport}" }
    if "servicesDetails" in dict_ and "availableServices" in dict_:
        dict_["servicesDetails"].append(service)
        if "REST" not in dict_["availableServices"]:
            dict_["availableServices"].append("REST")
    return service

def _addMQTT(dict_ : dict, **kwargs):
    """Add the MQTT service information to the dictionary."""

    service = {
        "serviceType" : "MQTT",
        "subscribedTopics" : [],
        "publishedTopics" : []
    }

    if "subscribedTopics" in kwargs:
        service["subscribedTopics"] = kwargs["subscribedTopics"]

    if "publishedTopics" in kwargs:
        service["publishedTopics"] = kwargs["publishedTopics"]

    if "servicesDetails" in dict_ and "availableServices" in dict_:
        dict_["servicesDetails"].append(service)
        if "MQTT" not in dict_["availableServices"]:
            dict_["availableServices"].append("MQTT")
