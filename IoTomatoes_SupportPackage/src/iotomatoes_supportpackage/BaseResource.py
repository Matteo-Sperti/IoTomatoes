import json
import requests
import time

from .MyThread import RefreshThread
from .MQTTClient import BaseMQTTClient
from .ItemInfo import (
    isMQTT, measureType, actuatorType, PowerConsumption_kW
)


class BaseResource():
    def __init__(self, settings: dict):
        """Initialize the BaseResource class."""

        self.CompanyName = settings["CompanyName"]
        self.platform_url = settings["IoTomatoes_url"]
        self.start(settings)

    def start(self, info: dict):
        """ Start the endpoint as a resource.
        It registers the resource to the Resource Catalog and starts the RefreshThread."""

        self.EndpointInfo = self.register(info)
        self._RefreshThread = RefreshThread(
            self.platform_url + "/rc/" + self.CompanyName, self)
        if self.isMQTT:
            brokerip = self.platform_url.split(":")[1].replace("//", "")
            self._MQTTClient = BaseMQTTClient(
                self.platform_url, self, brokerip)
            self._MQTTClient.startMQTT()

    def restart(self):
        self.stop()
        self.start(self.EndpointInfo)

    def stop(self):
        self._RefreshThread.stop()
        if self.isMQTT:
            self._MQTTClient.stopMQTT()

    def register(self, info: dict) -> dict:
        """Register the resource to the Resource Catalog."""

        while True:
            try:
                url = self.platform_url + "/rc/" + self.CompanyName + "/device"
                print(f"Registering to {url} ...")
                res = requests.post(url, json=info)
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
        return self.EndpointInfo["ID"]

    @property
    def isMQTT(self) -> bool:
        return isMQTT(self.EndpointInfo)

    @property
    def field(self) -> int:
        """Return the field of the resource."""
        try:
            return self.EndpointInfo["fieldNumber"]
        except:
            return -1

    @property
    def isActuator(self) -> bool:
        if "isActuator" not in self.EndpointInfo:
            return False
        else:
            return self.EndpointInfo["isActuator"]

    @property
    def isSensor(self) -> bool:
        if "isSensor" not in self.EndpointInfo:
            return False
        else:
            return self.EndpointInfo["isSensor"]

    @property
    def measureType(self) -> list:
        return measureType(self.EndpointInfo)

    @property
    def actuatorType(self) -> list:
        return actuatorType(self.EndpointInfo)

    @property
    def PowerConsumption_kW(self) -> int:
        return PowerConsumption_kW(self.EndpointInfo)

    def __str__(self):
        """Return a string with the information of the resource."""

        dict = {
            "ID": self.ID,
            "CompanyName": self.CompanyName,
            "EndpointInfo": self.EndpointInfo
        }

        return json.dumps(dict, indent=4)
