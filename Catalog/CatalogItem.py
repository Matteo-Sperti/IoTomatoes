import json
import time

class Service():
    def __init__(self, serviceName : str, availableServices : list = [], servicesDetails : list = []):
        self._struct = {
            "ID" : 0,
            "serviceName" : serviceName,
            "availableServices": availableServices,
            "servicesDetails": servicesDetails,
            "lastUpdate": time.time()
        }

    @property
    def ID(self) -> int:
        return self._struct["ID"]

    @property
    def serviceName(self) -> str:
        return self._struct["serviceName"]

    @property
    def availableServices(self) -> list:
        return self._struct["availableServices"]

    @property
    def servicesDetails(self) -> list:
        return self._struct["servicesDetails"]

    @property
    def lastUpdate(self) -> float:
        return self._struct["lastUpdate"]

    @serviceName.setter
    def serviceName(self, serviceName : str):
        self._struct["serviceName"] = serviceName
        self.refresh()

    @ID.setter
    def ID(self, ID : int):
        self._struct["ID"] = ID
        self.refresh()

    def addService(self, service : str, serviceInfo : dict = {}):
        self._struct["availableServices"].append(service)
        if "serviceType" not in serviceInfo:
            serviceInfo["serviceType"] = service
        else:
            if serviceInfo["serviceType"] != service:
                raise Exception("Service type and service name are different")

        self._struct["servicesDetails"].append(serviceInfo)
        self.refresh()

    def refresh(self):
        self._struct["lastUpdate"] = time.time()

    def __dict__(self):
        return self._struct

    def __str__(self) -> str:
        return json.dumps(self._struct)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Service):
            if self._struct["ID"] == __o._struct["ID"] and self._struct["serviceName"] == __o._struct["serviceName"]:
                return True
        return False

class Company():
    def __init__(self):
        self._struct = {
                    "ID": ID,
                    "name": params["name"],
                    "adminID": 1,
                }

class Device():
    def __init__(self):
        self._struct = {
            "deviceName": "DHT11",
            "companyName" : "MySmartThingy",
            "ServiceCatalog_url" : "http://localhost:8080/ServiceCatalog",
            "isActuator" : true,
            "isSensor" : true,
            "PowerConsumption_kW" : 9600,
            "measureType": [
                "Temperature",
                "Humidity"
            ],
            "availableServices": [
                "MQTT",
                "REST"
            ],
            "servicesDetails": [
                {
                    "serviceType": "MQTT",
                    "topic": [
                        "MySmartThingy/1/temp",
                        "MySmartThingy/1/hum"
                    ]
                },
                {
                    "serviceType": "REST",
                    "serviceIP": "dht11.org:8080"
                }
            ]
        }



class User():
    def __init__(self):
        self._struct = {
            "Name": "Pino",
            "Surname" : "Daniele",
            "Company" : "Pino Srl",
            "TelegramID": 12313123123,
            "ServiceCatalog_url" : "http://localhost:8080/ServiceCatalog"
        }

