import time

from MyExceptions import InfoException

def getID(dict_ : dict) -> int:
    if "ID" not in dict_:
        raise InfoException("ID is missing")   
    else:
        return dict_["ID"]

def getCompanyName(dict_ : dict) -> str:
    if "CompanyName" not in dict_:
        raise InfoException("Company name is missing")
    else:
        return dict_["CompanyName"]

def getField(dict_ : dict) -> int:
    return dict_["field"]

def isActuator(dict_ : dict) -> bool:
    if "isActuator" not in dict_:
        raise InfoException("isActuator is missing")
    else:
        return dict_["isActuator"]

def isSensor(dict_ : dict) -> bool:
    if "isSensor" not in dict_:
        raise InfoException("isSensor is missing")
    else:
        return dict_["isSensor"]

def measureType(dict_ : dict) -> list:
    if "measureType" not in dict_:
        raise InfoException("measureType is missing")
    else:
        return dict_["measureType"]

def actuators(dict_ : dict) -> list:
    if "actuators" not in dict_:
        raise InfoException("actuators is missing")
    else:
        return dict_["actuators"]

def PowerConsumption_kW(dict_ : dict) -> int:
    if "PowerConsumption_kW" not in dict_:
        raise InfoException("PowerConsumption_kW is missing")
    else:
        return dict_["PowerConsumption_kW"]

def isMQTT(dict_ : dict) -> bool:
    for service in dict_["availableServices"]:
        if service == "MQTT":
            return True
    return False

def subscribedTopics(dict_ : dict) -> list:
    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["subscribedTopics"]
    return []

def publishedTopics(dict_ : dict) -> list:
    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["publishedTopics"]
    return []

def getIPaddress(dict_ : dict) -> str:
    for service in dict_["servicesDetails"]:
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

def constructService(ID : int, EInfo : dict):
    info = {}
    info["ID"] = ID
    _makeService(EInfo, info)
    info["lastUpdate"] = time.time()
    return info

def constructResource(ID : int, CompInfo : dict, EInfo : dict):
    info = {}
    info["ID"] = ID
    _makeResource(EInfo, CompInfo, info)
    info["lastUpdate"] = time.time()
    return info

def _makeService(EInfo : dict, info : dict = {}):
    if "serviceName" not in EInfo:
        raise InfoException("Service name is missing")
    info["serviceName"] = EInfo["serviceName"]

    info["availableServices"] = []
    info["servicesDetails"] = []

    if "availableServices" in EInfo:
        if len(EInfo["availableServices"]) != len(EInfo["servicesDetails"]):
            raise InfoException("Available services and details are different")
        for i in range(len(EInfo["availableServices"])):
            if EInfo["availableServices"][i] in ["REST", "MQTT"]:
                _addService(info, EInfo["availableServices"][i], EInfo["servicesDetails"][i])
            else:
                raise InfoException("Service not supported")

    if "IPport" in EInfo and "IPaddress" in EInfo:
        _setIPport(EInfo["IPaddress"], EInfo["IPport"], info)
    
    return info

def _makeResource(EInfo : dict, CompInfo : dict, info : dict = {}):
    info["availableServices"] = []
    info["servicesDetails"] = []

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
                "subscribedTopics": [],
                "publishedTopics": []
                }

    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuator" not in EInfo:
            raise InfoException("Actuators names is missing")
        info["isActuator"] = True
        info["actuator"] = EInfo["actuators"]
        for actuator in EInfo["actuators"]:
            MQTT_info["subscribedTopics"].append(f"{CompInfo['CompanyName']}/{info['field']}/{info['ID']}/{actuator}")
    else:
        info["isActuator"] = False
        info["actuator"] = []

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        info["isSensor"] = True
        info["measureType"] = EInfo["measureType"]
        for measure in EInfo["measureType"]:
            MQTT_info["publishedTopics"].append(f"{CompInfo['CompanyName']}/{info['field']}/{info['ID']}/{measure}")
    else:
        info["isSensor"] = False
        info["measureType"] = []
    
    if "PowerConsumption_kW" in EInfo:
        info["PowerConsumption_kW"] = EInfo["PowerConsumption_kW"]
    else:
        info["PowerConsumption_kW"] = 0

    _addService(info, "MQTT", MQTT_info)

    return info

def _setIPport(local_ip : str,  IPport : int, dict_ : dict = {}):
    service = {
        "serviceType" : "REST",
        "serviceIP" : f"http://{local_ip}:{IPport}" }
    if "servicesDetails" in dict_ and "availableServices" in dict_:
        dict_["servicesDetails"].append(service)
        dict_["availableServices"].append("REST")
    return service

def _addService(dict_ : dict, service : str, serviceInfo : dict = {}):
    if "serviceType" in serviceInfo and serviceInfo["serviceType"] != service:
        raise InfoException("Service type and service name are different")

    dict_["availableServices"].append(service)

    my_info = {}
    if service == "MQTT":
        my_info["serviceType"] = "MQTT"
        if "subscribedTopics" in serviceInfo:
            my_info["subscribedTopics"] = serviceInfo["subscribedTopics"]
        else:
            my_info["subscribedTopics"] = []

        if "publishedTopics" in serviceInfo:
            my_info["publishedTopics"] = serviceInfo["publishedTopics"]
        else:
            my_info["publishedTopics"] = []

    elif service == "REST":
        my_info["serviceType"] = "REST"
        if "serviceIP" in serviceInfo:
            my_info["serviceIP"] = serviceInfo["serviceIP"]
        elif "IPaddress" in serviceInfo and "IPport" in serviceInfo:
            my_info["serviceIP"] = f"http://{serviceInfo['IPaddress']}:{serviceInfo['IPport']}"
        else:
            raise InfoException("Service IP is missing")
            
    else:
        if "serviceType" in serviceInfo:
            my_info.update(serviceInfo)
        else:
            my_info["serviceType"] = service
            my_info.update(serviceInfo)

    dict_["servicesDetails"].append(my_info)