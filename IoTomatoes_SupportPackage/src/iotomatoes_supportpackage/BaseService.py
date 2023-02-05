import requests
import time

from iotomatoes_supportpackage.ItemInfo import isMQTT
from iotomatoes_supportpackage.RefreshThread import RefreshThread
from iotomatoes_supportpackage.MQTTClient import BaseMQTTClient

class BaseService() :
    def __init__(self, settings: dict):
        """Initialize the BaseService class."""
        self._ServiceCatalog_url = settings["ServiceCatalog_url"]
        self.start(settings)

    def getCompaniesList(self):
        """Return the complete list of the companies from the Resource Catalog""" 

        try:
            r = requests.get(self.ResourceCatalog_url+"/companies")
            r.raise_for_status()
            companyList = r.json()
        except:
            print("ERROR: Resource Catalog not reachable!")
            return []
        else:
            return companyList

    def start(self, info: dict):
        """ Start the endpoint as a service.
        It registers the service to the Service Catalog and starts the RefreshThread."""

        self._EndpointInfo = self.register(info)
        self._RefreshThread = RefreshThread(self._ServiceCatalog_url, self)
        if self.serviceName != "ResourceCatalog":
            self.ResourceCatalog_url = self.getOtherServiceURL("resource_catalog", True)
        if self.isMQTT:
            self._MQTTClient = BaseMQTTClient(self._ServiceCatalog_url, self)
            self._MQTTClient.startMQTT()


    def restart(self):
        """Restart the endpoint as a service.
        It stops the RefreshThread and the MQTTClient and starts them again."""

        self.stop()
        self.start(self._EndpointInfo)

    def stop(self):
        self._RefreshThread.stop()
        if self.isMQTT:
            self._MQTTClient.stopMQTT()

    def register(self, info: dict) -> dict:
        """Register the service to the Service Catalog."""

        while True:
            try:
                res = requests.post(self._ServiceCatalog_url + "/insert", 
                                        json = info)
                res.raise_for_status()
                res_dict = res.json()
            except requests.exceptions.HTTPError as err:
                print(f"{err.response.status_code} : {err.response.reason}")
                time.sleep(1)
            except:
                print(f"Connection Error\nRetrying connection\n")
                time.sleep(1)
            else:
                try:                    
                    if "ID" in res_dict:
                        print("Service registered to the Service Catalog")
                        return res_dict
                except:
                    print(f"Error in the response\n")  
                    time.sleep(1)

    def getOtherServiceURL(self, serviceName: str, repeat : bool = False):
        """Return the URL of the service `serviceName`"""

        while repeat:
            try:
                r = requests.get(self._ServiceCatalog_url +"/" + serviceName + "/url")
                r.raise_for_status()
                res_dict = r.json()
            except:
                print("ERROR: Service Catalog not reachable!")
                time.sleep(1)
            else:
                if "url" in res_dict:
                    return res_dict["url"]
                else:
                    time.sleep(1)
        return ""
    
    @property
    def serviceName(self) -> str:
        return self._EndpointInfo["serviceName"]
    
    @property
    def ID(self) -> int:
        return self._EndpointInfo["ID"]
    
    @property
    def isMQTT(self) -> bool:
        return isMQTT(self._EndpointInfo)

    
