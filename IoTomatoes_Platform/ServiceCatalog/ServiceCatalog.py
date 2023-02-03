import json
import cherrypy
import time
import signal
import sys

from iotomatoes_supportpackage.MyExceptions import web_exception, InfoException
from iotomatoes_supportpackage.MyThread import MyThread
from iotomatoes_supportpackage.MyIDGenerator import IDs
from iotomatoes_supportpackage.ItemInfo import getIPaddress, constructService


serviceList_Name = "servicesList"

class ServiceCatalogManager:
    def __init__(self, heading : dict, filename = "catalog.json", autoDeleteTime = 120, IDs = IDs(1,99)):
        """Initialize the catalog manager.

        Arguments: \n
        `heading` is a dictionary with the heading of the catalog.\n
        `filename` is the name of the file to save the catalog in.\n
        `autoDeleteTime` is the time in seconds after which the items are deleted from the catalog if not refreshed (default is 120). \n
        `IDs` is the ID generator object to use for the services (default is integer from 1 to 99).\n
        """
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.IDs = IDs
        self.catalog = heading.copy()
        self.catalog["lastUpdate"] = time.time()
        self.catalog[serviceList_Name] = []
        self.autoDeleteItemsThread = MyThread(self.autoDeleteItems, interval=self.autoDeleteTime)

    def save(self):
        """Save the catalog in the file specified in the initialization. 

        Return: json with the status of the operation."""
        
        json.dump(self.catalog, open(self.filename, "w"), indent=4)
        print("Catalog saved!\n")
        return json.dumps({"Status": True}, indent=4)

    def print_catalog(self):
        """Return the catalog in json format."""
        
        return json.dumps(self.catalog, indent=4)

    @property
    def broker(self):
        """Return the broker info in json format."""

        try:
            return json.dumps(self.catalog["broker"], indent=4)
        except KeyError:
            raise web_exception(404, "Broker info not found")
        
    @property
    def telegramToken(self):
        """Return the telegram token in json format."""

        try:
            return json.dumps({"telegramToken": self.catalog["telegramToken"]}, indent=4)
        except KeyError:
            raise web_exception(404, "Telegram token not found")

    def get_all(self):
        """Return a json with all the services"""

        try:
            return json.dumps(self.catalog[serviceList_Name], indent=4)
        except KeyError:
            raise web_exception(404, "List not found")

    def getService_url(self, service : str):
        """Return the url of item `ID` in json format.

        `ID` is the ID of the item to return the information of.
        """
        try:
            ID = int(service)
            item = self.find_item(ID=ID)
        except ValueError:
            item = self.find_item(serviceName=service)

        if item != None:
            out = {"url": getIPaddress(item)}
            return json.dumps(out, indent=4)
        raise web_exception(404, "Service info not found")

    def insert(self, item_dict : dict):
        """Insert a new service in the catalog.
        Return a json with the status of the operation.
        
        Arguments:
        `item_dict` is the service in json format to insert.
        """
        try:
            ID = self.IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] = time.time() 
                try:
                    new_item = constructService(ID, item_dict)
                except InfoException as e:
                    raise web_exception(500, e.message)
                self.catalog[serviceList_Name].append(new_item)
                out = new_item.copy()
                return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def delete(self, IDvalue : int):
        """Delete a service from the catalog.
        Return a json with the status of the operation.
        
        Arguments:
        `IDvalue` is the ID of the service to delete.
        """
        try:
            item = self.find_item(ID=IDvalue)
            if item != None : 
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                self.catalog[serviceList_Name].remove(item)
                self.IDs.free_ID(IDvalue)
                out = {"Status": True}
            else:
                out = {"Status": False}
            return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")


    def find_item(self, **kwargs):
        """Return the service with the ID `IDvalue`."""

        if "ID" in kwargs:
            key = "ID"
            value =  int(kwargs["ID"])
        elif "serviceName" in kwargs:
            value = kwargs["serviceName"]
            key = "serviceName"
        else:
            return None
        
        for item in self.catalog[serviceList_Name]:
            if item[key] == value:
                return item
        return None


        return None

    def refreshItem(self, IDvalue : int):
        """Refresh the lastUpdate field of a service.
        Return a json with the status of the operation.

        Arguments:
        `IDvalue` is the ID of the service to refresh.
        """

        item = self.find_item(ID=IDvalue)
        if item != None:
            actualtime = time.time()
            self.catalog["lastUpdate"] = actualtime
            item["lastUpdate"] = actualtime
            out = {"Status": True}
        else:
            out = {"Status": False}
        return json.dumps(out, indent=4)

    def autoDeleteItems(self):
        """Refresh the catalog removing the services that are not online anymore."""

        actualtime = time.time()
        for key in self.catalog:
            if isinstance(self.catalog[key], list):
                for device in self.catalog[key]:
                    try:
                        if actualtime - device["lastUpdate"] > self.autoDeleteTime:
                            self.IDs.free_ID(device["ID"])
                            print(f"""Device {device["ID"]} removed""")
                            self.catalog[key].remove(device)
                    except KeyError:
                        print("Device without lastUpdate field")
                        self.catalog[key].remove(device)
        self.catalog["lastUpdate"] = actualtime
        self.save()

class RESTServiceCatalog():
    exposed = True

    def __init__(self, settings : dict):
        """ Initialize the RESTServiceCatalog class.

        Arguments:\n
        `heading` is the heading of the catalog.\n
        `name` is the name of the catalog.\n
        `filename` is the name of the file to save the catalog.\n
        `autoDeleteTime` is the time in seconds to delete the services that are not online anymore.\n
        """
        heading = {
            "owner": settings["owner"], 
            "CatalogName": settings["CatalogName"],
            "broker": settings["broker"],
            "telegramToken" : settings["telegramToken"]
            }
        self._systemToken = settings["SystemToken"]
        self.ServiceCatalog = ServiceCatalogManager(heading, settings["filename"], settings["autoDeleteTime"])

    def close(self):
        """Close the endpoint and save the catalog."""

        self.ServiceCatalog.autoDeleteItemsThread.stop()
        self.ServiceCatalog.save()

    def GET(self, *uri, **params):
        """REST GET method.

        Allowed commands:\n
        `/all` to get all the services.\n
        `/broker` to get the broker info.\n
        `/telegram` to get the telegram token.\n
        `/<servicename>/url to get the url of a service
        """
        try:
            if len(uri) == 0:
                raise web_exception(404, "No command received")
            elif len(uri) == 1 and uri[0] == "all":
                return self.ServiceCatalog.get_all()
            elif len(uri) == 1 and uri[0] == "broker":
                return self.ServiceCatalog.broker
            elif len(uri) == 1 and uri[0] == "telegram":
                return self.ServiceCatalog.telegramToken
            elif len(uri) == 2 and uri[1] == "url":
                return self.ServiceCatalog.getService_url(uri[0])
            else:
                raise web_exception(404, "Invalid Command")

        except web_exception as e:
            print(e.message)
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            e_string = "Server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)
        
    def PUT(self, *uri, **params):
        """PUT REST method.

        Allowed commands:\n
        `/refresh?ID=<ID>` to refresh the lastUpdate field of a service by ID.\n
        """
        try:
            if len(uri) == 1 and uri[0] == "refresh":
                if "ID" in params:
                    return self.ServiceCatalog.refreshItem(int(params["ID"]))
                else:
                    raise web_exception(400, "Invalid parameter")
            else:
                raise web_exception(404, "Invalid command")
        except web_exception as e:
            print(e.message)
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

    def POST(self, *uri, **params):
        """POST REST method.
        
        Allowed commands:\n
        `/save` to save the catalog in the file.\n
        `/insert` to insert a new service in the catalog. 
        The body of the request must contain the new service info.
        """
        try:
            if len(uri) == 1 and uri[0] == "save":
                return self.ServiceCatalog.save()
            elif len(uri) == 1 and uri[0] == "insert":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.ServiceCatalog.insert(body_dict)
            else:
                raise web_exception(404, "Invalid command")
        except web_exception as e:
            print(e.message)
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

    def DELETE(self, *uri, **params):
        """DELETE REST method.

        Allowed commands:\n
        `/delete?ID=<ID>` to delete a service by ID.
        """
        try:
            if len(uri) == 1 and uri[0] == "delete":
                if "ID" in params:
                    return self.ServiceCatalog.delete(int(params["ID"]))
                else:
                    raise web_exception(400, "Invalid parameter")
            else:
                raise web_exception(404, "Invalid command")
        except web_exception as e:
            print(e.message)
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

def sigterm_handler(signal, frame):
    Catalog.close()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")

signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    settings = json.load(open("ServiceCatalogSettings.json"))

    port = settings["IPport"]

    Catalog = RESTServiceCatalog(settings)

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(Catalog, '/', conf)
    cherrypy.config.update({'server.socket_host': "0.0.0.0"})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()