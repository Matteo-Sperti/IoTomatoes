import json
import cherrypy
import time
import sys
import socket

sys.path.append("../SupportClasses/")
from MyExceptions import *
from MyThread import MyThread
from MyIDGenerator import IDs
from ItemInfo import EndpointInfo as EInfo

serviceList_Name = "servicesList"

class ServiceCatalogManager:
    def __init__(self, heading : dict, filename = "catalog.json", autoDeleteTime = 120, IDs = IDs(1,99)):
        """Initialize the catalog manager.
        Keyword arguments:
        ``heading`` is a dictionary with the heading of the catalog,
        ``filename`` is the name of the file to save the catalog in,
        ``autoDeleteTime`` is the time in seconds after which the items are deleted from the catalog if not refreshed.
        """
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.IDs = IDs
        self.catalog = heading
        self.catalog["lastUpdate"] = time.time()
        self.catalog[serviceList_Name] = []
        self.autoDeleteItemsThread = MyThread(self.autoDeleteItems, interval=self.autoDeleteTime)

    def save(self):
        """Save the catalog in the file specified in the initialization."""
        
        json.dump(self.catalog, open(self.filename, "w"), indent=4)
        print("Catalog saved!\n")
        return json.dumps({"Status": True}, indent=4)

    def print_catalog(self):
        """Return the catalog in json format."""
        
        return json.dumps(self.catalog, indent=4)

    def load(self):
        """Load the catalog from the file specified in the initialization."""

        try:
            self.catalog = json.load(open(self.filename, "r"))
            print("Catalog loaded!\n")
            return json.dumps({"Status": True}, indent=4)
        except FileNotFoundError:
            print("Catalog file not found!\n")
            return json.dumps({"Status": False}, indent=4)

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

    def get(self, info : str, ID : int):
        """Return the REST or MQTT information of item ``ID`` in json format.

        Keyword arguments:
        ``info`` is the type of information to return (REST, MQTT) and
        ``ID`` is the ID of the item to return the information of.
        """
        item = self.find_item(ID)

        if item != None:
            if "servicesDetails" in item:
                 for serviceInfo in item["servicesDetails"]:
                    if serviceInfo["serviceType"] == info:
                        return json.dumps(serviceInfo, indent=4)
        raise web_exception(404, "Service info not found")

    def search(self, key : str, value):
        """Search for a item in the catalog.
        Return a json with the item if found, otherwise return an empty list.

        Keyword arguments: 
        ``key`` is the key to search for and
        ``value``is the value to search for.
        """
        try:      
            output = []
            for service in self.catalog[serviceList_Name]:
                if isinstance(service[key], list):
                    if value in service[key]:
                        output.append(service)
                else:
                    if str(service[key]) == str(value):
                        output.append(service)
            return json.dumps(output, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def insert(self, item_dict : dict):
        """Insert a new device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``item_dict`` is the item in json format to insert.
        """
        try:
            ID = self.IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] = time.time() 
                try:
                    new_item = EInfo(isService=True).constructService(ID, item_dict)
                except InfoException as e:
                    raise web_exception(500, e.message)
                self.catalog[serviceList_Name].append(new_item)
                out = {"ID": ID}
                return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def update(self, ID : int, new_item : dict):
        """Update a device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``ID`` is the ID of the item to update and
        ``new_item`` is the item in json format to update.
        """

        item = self.find_item(ID)
        if item != None:
            actualtime = time.time()
            self.catalog["lastUpdate"] = actualtime
            for key in item:
                if key in new_item:
                    item[key] = new_item[key]
            item["ID"] = ID
            item["lastUpdate"] = actualtime
            out = {"Status": True}
        else:
            out = {"Status": False}
        return json.dumps(out, indent=4)

    def delete(self, IDvalue : int):
        """Delete a item from the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``IDvalue`` is the ID of the item to delete.
        """
        try:
            item = self.find_item(IDvalue)
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


    def find_item(self, IDvalue : int) :
        """Return the item with the ID ``IDvalue``."""

        for item in self.catalog[serviceList_Name]:
            if item["ID"] == IDvalue:
                return item
        return None

    def refreshItem(self, IDvalue : int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Keyword arguments:
        ``IDvalue`` is the ID of the item to refresh.
        """

        item = self.find_item(IDvalue)
        if item != None:
            actualtime = time.time()
            self.catalog["lastUpdate"] = actualtime
            item["lastUpdate"] = actualtime
            out = {"Status": True}
        else:
            out = {"Status": False}
        return json.dumps(out, indent=4)

    def autoDeleteItems(self):
        """Refresh the catalog removing the devices that are not online anymore."""

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


class RESTServiceCatalog():
    exposed = True

    def __init__(self, settings : dict):
        """ Initialize the RESTServiceCatalog class.

        Keyword arguments:\n
        ``heading`` is the heading of the catalog.\n
        ``name`` is the name of the catalog.\n
        ``filename`` is the name of the file to save the catalog.\n
        ``autoDeleteTime`` is the time in seconds to delete the services that are not online anymore.\n
        """
        heading = {
            "owner": settings["owner"], 
            "CatalogName": settings["CatalogName"],
            "broker": settings["broker"],
            "telegramToken" : settings["telegramToken"],
            }

        self.ServiceCatalog = ServiceCatalogManager(heading, settings["filename"], settings["autoDeleteTime"])

    def GET(self, *uri, **params):
        """REST GET method.

        Allowed commands:\n
        ``/get/<info>?ID=<ID>`` to get a service info by ID, where ``<info>`` is ``REST`` or ``MQTT``.\n 
        ``/getall`` to get all the services.\n
        ``/broker`` to get the broker info.\n
        ``/telegram`` to get the telegram toke.\n
        ``/search/<info>?<info>=<value>`` to search a service by info.
        """
        try:
            if len(uri) == 0:
                raise web_exception(404, "No command received")
            elif len(uri) == 2 and uri[0] == "get" and uri[1] in ["REST", "MQTT"]:
                if "ID" in params:
                    return self.ServiceCatalog.get(uri[1], int(params["ID"]))
                else:
                    raise web_exception(400, "Invalid parameter")
            elif len(uri) == 1 and uri[0] == "getall":
                return self.ServiceCatalog.get_all()
            elif len(uri) == 1 and uri[0] == "broker":
                return self.ServiceCatalog.broker
            elif len(uri) == 1 and uri[0] == "telegram":
                return self.ServiceCatalog.telegramToken
            elif len(uri) == 2 and uri[0] == "search":
                if uri[1] in params:
                    return self.ServiceCatalog.search(uri[1], params[uri[1]])
                else: 
                    raise web_exception(400, "Invalid parameter")
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
        ``/update`` to update the catalog.
        The body of the request must contain the new service info in json format. \n
        ``/refresh?ID=<ID>`` to refresh the lastUpdate field of a service by ID.\n
        """
        try:
            if len(uri) == 1 and uri[0] == "update":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.ServiceCatalog.update(int(params["ID"]), body_dict)
            elif len(uri) == 1 and uri[0] == "refresh":
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
        ``/save`` to save the catalog in the file.\n
        ``/insert`` to insert a new service in the catalog. 
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
        ``/delete?ID=<ID>`` to delete a service by ID.
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


if __name__ == "__main__":
    settings = json.load(open("ServiceCatalogSettings.json"))

    local_ip = socket.gethostbyname(socket.gethostname())
    port = settings["IPport"]

    Catalog = RESTServiceCatalog(settings)

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(Catalog, '/', conf)
    cherrypy.config.update({'server.socket_host': local_ip})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()
    
    cherrypy.engine.block()
    Catalog.ServiceCatalog.save()
    print("Server stopped")