import time
from socket import gethostname, gethostbyname
from .MyExceptions import InfoException

### Get item information from a dictionary ###


def measureType(dict_: dict) -> list:
    if "measureType" not in dict_:
        raise InfoException("measureType is missing")
    else:
        return dict_["measureType"]


def actuatorType(dict_: dict) -> list:
    if "actuatorType" not in dict_:
        raise InfoException("actuatorType is missing")
    else:
        return dict_["actuatorType"]


def PowerConsumption_kW(dict_: dict) -> int:
    if "PowerConsumption_kW" not in dict_:
        raise InfoException("PowerConsumption_kW is missing")
    else:
        return dict_["PowerConsumption_kW"]


def isMQTT(dict_: dict) -> bool:
    if "availableServices" not in dict_:
        return False

    for service in dict_["availableServices"]:
        if service == "MQTT":
            return True
    return False


def subscribedTopics(dict_: dict) -> list:
    if "servicesDetails" not in dict_:
        return []

    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["subscribedTopics"]
    return []


def publishedTopics(dict_: dict) -> list:
    if "servicesDetails" not in dict_:
        return []

    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "MQTT":
            return service["publishedTopics"]
    return []


def getIPaddress(dict_: dict) -> str:
    if "servicesDetails" not in dict_:
        return ""

    for service in dict_["servicesDetails"]:
        if service["serviceType"] == "REST":
            return service["serviceIP"]
    return ""

### Construct item dictionary according to the specification of the catalog ###


def constructService(ID: int, EInfo: dict):
    """ Construct the dictionary of a service according to the specification of the catalog.

    Arguments:
    - `ID (int)`: The ID of the service.
    - `EInfo (dict)`: The dictionary containing the information of the service.

    Returns:
    - `dictInformation (dict)`: The dictionary of the service.
    """
    dictInformation = {}
    dictInformation["ID"] = ID
    _makeService(dictInformation, EInfo)
    dictInformation["lastUpdate"] = time.time()
    return dictInformation


def constructResource(ID: int, CompName: str, EInfo: dict):
    """ Construct the dictionary of a resource according to the specification of the catalog.

    Arguments:
    - `ID (int)`: The ID of the resource.
    - `CompName (str)`: The name of the company of the resource.
    - `EInfo (dict)`: The dictionary containing the information of the resource.

    Returns:
    `dictInformation (dict)`: The dictionary of the resource.\n
    """
    dictInformation = {}
    dictInformation["ID"] = ID
    _makeResource(dictInformation, EInfo)
    _makeResourceTopic(dictInformation, EInfo, CompName)
    dictInformation["lastUpdate"] = time.time()
    return dictInformation


def _makeResourceTopic(dictInformation: dict, EInfo: dict, CompanyName: str):
    """If the resource is a sensor or an actuator, add the MQTT topics to the dictionary.

    Arguments:
    - `dictInformation (dict)`: The dictionary of the resource to be modified.
    - `EInfo (dict)`: The dictionary containing the information of the resource.
    - `CompanyName (str)`: The name of the company of the resource.
    """

    if "ID" not in dictInformation:
        raise InfoException("ID is missing")

    subscribedTopics = []
    publishedTopics = []

    CompanyTopic = CompanyName.replace(" ", "_")
    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuatorType" not in EInfo:
            raise InfoException("Actuators names is missing")
        for actuator in EInfo["actuatorType"]:
            subscribedTopics.append(
                f"{CompanyTopic}/{EInfo['fieldNumber']}/{dictInformation['ID']}/{actuator}")

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        for measure in EInfo["measureType"]:
            publishedTopics.append(
                f"{CompanyTopic}/{EInfo['fieldNumber']}/{dictInformation['ID']}/{measure}")

    _addMQTT(dictInformation, subscribedTopics=subscribedTopics,
             publishedTopics=publishedTopics)


def _makeResource(dictInformation: dict, EInfo: dict):
    """Construct the dictionary of a resource according to the specification of the catalog.

    Arguments:
    - `dictInformation (dict)`: The dictionary of the resource to be modified.
    - `EInfo (dict)`: The dictionary containing the information of the resource.
    """

    dictInformation["availableServices"] = []
    dictInformation["servicesDetails"] = []

    if "deviceName" not in EInfo:
        raise InfoException("Device name is missing")
    else:
        dictInformation["deviceName"] = EInfo["deviceName"]

    if "fieldNumber" in EInfo:
        dictInformation["fieldNumber"] = EInfo["fieldNumber"]
    else:
        dictInformation["fieldNumber"] = 0
        EInfo["fieldNumber"] = 0

    if "latitude" in EInfo and "longitude" in EInfo:
        dictInformation["Location"] = {
            "latitude": EInfo["latitude"],
            "longitude": EInfo["longitude"]
        }
    elif "Location" in EInfo and "latitude" in EInfo["Location"] and "longitude" in EInfo["Location"]:
        dictInformation["Location"] = EInfo["Location"]
    else:
        dictInformation["Location"] = {
            "latitude": -1,
            "longitude": -1
        }

    if "PowerConsumption_kW" in EInfo:
        dictInformation["PowerConsumption_kW"] = EInfo["PowerConsumption_kW"]
    else:
        dictInformation["PowerConsumption_kW"] = 0

    if "isActuator" in EInfo and EInfo["isActuator"] == True:
        if "actuatorType" not in EInfo:
            raise InfoException("Actuators names is missing")
        dictInformation["isActuator"] = True
        dictInformation["actuatorType"] = EInfo["actuatorType"]
    else:
        dictInformation["isActuator"] = False
        dictInformation["actuatorType"] = []

    if "isSensor" in EInfo and EInfo["isSensor"] == True:
        if "measureType" not in EInfo:
            raise InfoException("Measure type is missing")
        dictInformation["isSensor"] = True
        dictInformation["measureType"] = EInfo["measureType"]
    else:
        dictInformation["isSensor"] = False
        dictInformation["measureType"] = []


def _makeService(dictInformation: dict, EInfo: dict):
    """Construct the dictionary of a service according to the specification of the catalog.

    Arguments:
    - `dictInformation (dict)`: The dictionary of the service to be modified.
    - `EInfo (dict)`: The dictionary containing the information of the service.
    """

    if "serviceName" not in EInfo:
        raise InfoException("Service name is missing")
    dictInformation["serviceName"] = EInfo["serviceName"]

    dictInformation["availableServices"] = []
    dictInformation["servicesDetails"] = []

    if "availableServices" in EInfo:
        if "MQTT" in EInfo["availableServices"]:
            serviceInfo = {}
            if "servicesDetails" in EInfo:
                for service in EInfo["servicesDetails"]:
                    if "serviceType" in service and service["serviceType"] == "MQTT":
                        serviceInfo = service
                        break
            _addMQTT(dictInformation, **serviceInfo)
        if "REST" in EInfo["availableServices"]:
            serviceInfo = {}
            if "servicesDetails" in EInfo:
                for service in EInfo["servicesDetails"]:
                    if "serviceType" in service and service["serviceType"] == "REST":
                        serviceInfo = service
                        break
            _addREST(dictInformation, **serviceInfo)


def _addREST(dictInformation: dict, **kwargs):
    """Add the REST service information to the dictionary."""

    if "serviceIP" in kwargs:
        service = {
            "serviceType": "REST",
            "serviceIP": kwargs["serviceIP"]}
    else:
        if "IPaddress" not in kwargs:
            raise InfoException("IP address is missing")
        local_ip = kwargs["IPaddress"]

        if "IPport" in kwargs:
            IPport = kwargs["IPport"]
        else:
            IPport = 8080

        service = {
            "serviceType": "REST",
            "serviceIP": f"http://{local_ip}:{IPport}"}

    _addService(dictInformation, service)


def _addMQTT(dictInformation: dict, **kwargs):
    """Add the MQTT service information to the dictionary."""

    if kwargs == {}:
        if "availableServices" in dictInformation:
            dictInformation["availableServices"].append("MQTT")
        else:
            dictInformation["availableServices"] = ["MQTT"]
    else:
        service = {
            "serviceType": "MQTT",
            "subscribedTopics": [],
            "publishedTopics": []
        }

        if "subscribedTopics" in kwargs:
            service["subscribedTopics"] = kwargs["subscribedTopics"]

        if "publishedTopics" in kwargs:
            service["publishedTopics"] = kwargs["publishedTopics"]

        _addService(dictInformation, service)


def _addService(dictInformation: dict, service2add: dict):
    """Add the service information to the dictionary.

    Arguments:\n
    - `dictInformation (dict)`: The dictionary of the resource to be modified.
    - `service2add (dict)`: The dictionary containing the information of 
    the service to be added
    """

    if "servicesDetails" in dictInformation:
        dictInformation["servicesDetails"].append(service2add)
    else:
        dictInformation["servicesDetails"] = [service2add]

    serviceName = service2add["serviceType"]
    if "availableServices" in dictInformation:
        if serviceName not in dictInformation["availableServices"]:
            dictInformation["availableServices"].append(serviceName)
    else:
        dictInformation["availableServices"] = [serviceName]


def setREST(settings: dict):
    """Set the REST service information.

    Arguments:
    - `settings (dict)`: The dictionary containing the information of the service.
    This dictionary is modified by the function.
    """
    ip_address = gethostbyname(gethostname())

    if "IPport" in settings:
        port = settings["IPport"]
    else:
        port = 8080

    _addREST(settings, IPaddress=ip_address, IPport=port)

    return ip_address, port
