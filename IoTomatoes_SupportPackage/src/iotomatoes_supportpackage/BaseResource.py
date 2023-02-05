import json
import requests
import time

from iotomatoes_supportpackage.RefreshThread import RefreshThread
from iotomatoes_supportpackage.MQTTClient import BaseMQTTClient
from iotomatoes_supportpackage.ItemInfo import (
    isMQTT, measureType, actuatorType, PowerConsumption_kW
)

class BaseResource() :
    def __init__(self, settings: dict):
        """Initialize the BaseResource class."""

        self.CompanyName = settings["CompanyName"]
        self.platform_url = settings["IoTomatoes_url"]
        self.start(settings)

    def start(self, info: dict) :        
        """ Start the endpoint as a resource.
        It registers the resource to the Resource Catalog and starts the RefreshThread."""

        self._EndpointInfo = self.register(info)
        self._RefreshThread = RefreshThread(self.platform_url + "/rc/" + self.CompanyName, self)
        if self.isMQTT:
            self._MQTTClient = BaseMQTTClient(self.platform_url, self._EndpointInfo, self.platform_url)
            self._MQTTClient.startMQTT()

    def restart(self):
        self.stop()
        self.start(self._EndpointInfo)

    def stop(self):
        self._RefreshThread.stop()
        if self.isMQTT:
            self._MQTTClient.stopMQTT()

    def register(self, info : dict) -> dict:
        """Register the resource to the Resource Catalog."""

        while True:
            try:
                url = self.platform_url + "/rc/" + self.CompanyName + "/device"
                print(f"Registering to {url} ...")
                res = requests.post(url, json = info)
                res.raise_for_status()
                res_dict = res.json()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:               
                if "ID" in res_dict:
                    print("Resource registered to the Resource Catalog")
                    return res_dict
                else:
                    print(f"Error in the response\n")
                    time.sleep(1)

    @property
    def ID(self) -> int:
        return self._EndpointInfo["ID"]
    
    @property
    def isMQTT(self) -> bool:
        return isMQTT(self._EndpointInfo)

    @property
    def field(self) -> int:
        """Return the field of the resource."""
        try:
            return self._EndpointInfo["field"]
        except:
            return -1

    @property
    def isActuator(self) -> bool:
        if "isActuator" not in self._EndpointInfo:
            return False
        else:
            return self._EndpointInfo["isActuator"]

    @property
    def isSensor(self) -> bool:
        if "isSensor" not in self._EndpointInfo:
            return False
        else:
            return self._EndpointInfo["isSensor"]

    @property
    def measureType(self) -> list:
        return measureType(self._EndpointInfo)

    @property
    def actuatorType(self) -> list:
        return actuatorType(self._EndpointInfo)

    @property
    def PowerConsumption_kW(self) -> int:
        return PowerConsumption_kW(self._EndpointInfo)

    def __str__(self):
        """Return a string with the information of the resource."""

        dict = {
            "ID": self.ID,
            "CompanyName": self.CompanyName,
            "EndpointInfo": self._EndpointInfo
        }

        return json.dumps(dict, indent=4)