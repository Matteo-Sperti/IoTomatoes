import json
import time
import cherrypy
import socket
import sys

sys.path.append("../SupportClasses/")
from GenericEndPoints import GenericService
from MyExceptions import *
from ItemInfo import ServiceInfo
from MyIDGenerator import IDs
from MyThread import MyThread

IDperCompany = 10000

def query_yes_no(question):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}


    while True:
        choice = input(question + " [Y/n] ").lower()
        if choice == "":
            return valid["yes"]
        elif choice in valid:
            return valid[choice]
        else:
            print(f"Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

class CatalogManager:
    def __init__(self, heading : dict, key_list : list, filename = "catalog.json", autoDeleteTime = 120, IDs = IDs(1,99)):
        """Initialize the catalog manager.
        Keyword arguments:
        ``heading`` is a dictionary with the heading of the catalog,
        ``key_list`` is a list of the keys of the lists to be added in the catalog and
        ``filename`` is the name of the file to save the catalog in.
        """
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.IDs = IDs
        self.catalog = heading
        self.catalog["lastUpdate"] = time.time(), 
        for key in key_list:
            self.catalog[key] = []
        self.autoDeleteItemsThread = MyThread(self.autoDeleteItems, interval=self.autoDeleteTime)

    def save(self):
        """Save the catalog in the file specified in the initialization."""
        
        json.dump(self.catalog, open(self.filename, "w"), indent=4)
        print("Catalog saved!\n")
        return json.dumps({"Status": True}, indent=4)

    def print_catalog(self):
        """Return the catalog in json format."""
        return json.dumps(self.catalog, indent=4)

    def to_dict(self):
        return self.catalog

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

    def get_all(self, list_key : str):
        """Return a json with all the items in the list specified in ``list_key``."""
        try:
            return json.dumps(self.catalog[list_key], indent=4)
        except KeyError:
            raise web_exception(404, "List not found")

    def get(self, info : str, ID : int):
        """Return the REST or MQTT information of item ``ID`` in json format.

        Keyword arguments:
        ``info`` is the type of information to return (REST, MQTT) and
        ``ID`` is the ID of the item to return the information of
        """
        item = self.find_item(ID)

        if item != None:
            if "servicesDetails" in item:
                 for serviceInfo in item["servicesDetails"]:
                    if serviceInfo["serviceType"] == info:
                        return json.dumps(serviceInfo, indent=4)
        raise web_exception(404, "Service info not found")

    def search(self, list_key : str, key : str, value):
        """Search for a item in the catalog.
        Return a json with the item if found, otherwise return an empty list.

        Keyword arguments: 
        ``list_key`` is the name of the list to search in, 
        ``key`` is the key to search for and
        ``value``is the value to search for
        """
        try:      
            output = []
            for device in self.catalog[list_key]:
                if isinstance(device[key], list):
                    if value in device[key]:
                        output.append(device)
                else:
                    if str(device[key]) == str(value):
                        output.append(device)
            return json.dumps(output, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def insert(self, list_key : str, new_item : dict):
        """Insert a new device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to insert in and
        ``new_item`` is the item in json format to insert
        """
        try:
            ID = self.IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                actualtime = time.time() 
                self.catalog["lastUpdate"] = actualtime
                new_item["ID"] = ID
                new_item["lastUpdate"] = actualtime
                self.catalog[list_key].append(new_item)
                out = {"ID": ID}
                return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def update(self, ID : int, new_item : dict):
        """Update a device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``ID`` is the ID of the item to update and
        ``new_item`` is the item in json format to update
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
        ``IDvalue`` is the ID of the item to delete
        """
        try:
            current_list = self.find_list(IDvalue)
            if current_list != None:
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                for i in range(len(current_list)):
                    if current_list[i]["ID"] == IDvalue:
                        current_list.pop(i)
                        self.IDs.free_ID(IDvalue)
                        break
                out = {"Status": True}
            else:
                out = {"Status": False}
            return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")
    
    def find_list(self, IDvalue : int):
        """Return the list where the item with the ID ``IDvalue`` is present."""
        for key in self.catalog:
            if isinstance(self.catalog[key], list):
                for item in self.catalog[key]:
                    if item["ID"] == IDvalue:
                        return self.catalog[key]
        return None

    def find_item(self, IDvalue : int) :
        """Return the item with the ID ``IDvalue``."""

        current_list = self.find_list(IDvalue)
        if current_list != None:
            for item in current_list:
                if item["ID"] == IDvalue:
                    return item
        return None

    def refreshItem(self, IDvalue : int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Keyword arguments:
        ``IDvalue`` is the ID of the item to refresh
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


class CompanyCatalog():
    def __init__(self, heading, filename = "CompanyCatalog.json", autoDeleteTime = 120, IDs = IDs(IDperCompany, step=IDperCompany)):
        self.heading = heading
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.IDs = IDs
        self.companiesList = []

    def insertCompany(self, CompanyInfo : dict, AdminInfo : dict):
        if "CompanyName" in CompanyInfo and  "CompanyToken" in CompanyInfo:
            ID = self.IDs.get_ID()
            if ID != -1:
                CompanyInfo = {
                    "ID": ID,
                    "CompanyName": CompanyInfo["CompanyName"],
                    "CompanyToken": CompanyInfo["CompanyToken"],
                    "adminID": 1,
                }
                if query_yes_no(f"Are you sure you want to add the company {CompanyInfo['CompanyName']}?"):
                    NewCompany = CatalogManager(CompanyInfo, ["devicesList", "usersList"], 
                                                autoDeleteTime=self.autoDeleteTime, IDs=IDs(ID+1, ID+IDperCompany-1))
                    AdminID = json.loads(NewCompany.insert("usersList", AdminInfo))["ID"]
                    NewCompany.catalog["adminID"] = AdminID
                    self.companiesList.append(NewCompany)
                    return {"Status": True, "CompanyID": ID, "CompanyToken": CompanyInfo["CompanyToken"]}
        
        return {"Status": False}

    def deleteCompany(self, CompanyID, userID):
        for company in self.companiesList:
            if company.catalog["ID"] == CompanyID:
                if company.catalog["adminID"] == userID:
                    if query_yes_no(f"Are you sure you want to delete the company {company.catalog['name']}?"):
                        self.companiesList.remove(company)
                        return {"Status": True}
                else:
                    raise web_exception(401, "You are not authorized to delete this company.")
        
        raise web_exception(404, "Company not found.") 

    def insertItem(self, type : str, CompanyID, iteminfo : dict):
        for company in self.companiesList:
            if company.catalog["ID"] == CompanyID:
                return company.insert(type.join("sList"), iteminfo)
        raise web_exception(404, "Company not found.")

    def refreshItem(self, CompanyID, ItemID):
        for company in self.companiesList:
            if company.catalog["ID"] == CompanyID:
                return company.refresh(ItemID)
        raise web_exception(404, "Company not found.")

    def deleteItem(self, type : str, CompanyID, itemID):
        for company in self.companiesList:
            if company.catalog["ID"] == CompanyID:
                return company.delete(type.join("sList"), itemID)
        raise web_exception(404, "Company not found.")

    def __dict__(self):
        CatalogDict = self.heading
        CatalogDict["companiesList"] = list()
        for company in self.companiesList:
            CatalogDict["companiesList"].append(company.to_dict())

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.__dict__(), f)


class RESTResourceCatalog(GenericService):
    exposed = True

    def __init__(self, Service_info : ServiceInfo, ServiceCatalog_url : str,
                     filename : str = "ResourceCatalog.json", autoDeleteTime :int = 120):  

        self.catalog = CompanyCatalog(Service_info, filename, autoDeleteTime)
        super().__init__(Service_info, ServiceCatalog_url)

    def GET(self, *uri, **params):
        pass

    def POST(self, *uri, **params):
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "insertCompany":
                    body_dict = json.loads(cherrypy.request.body.read())
                    print(body_dict, params)
                    return self.catalog.insertCompany(params, body_dict)
                elif len(uri) == 2 and uri [2] == "insert":
                    if uri[1] in ["user", "device"]:
                        body_dict = json.loads(cherrypy.request.body.read())
                        return self.catalog.insertItem(uri[2], params, body_dict)
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error.")
    
    def PUT(self, *uri, **params):
        try:
            if len(uri) > 0:
                if len(uri) == 3 and uri[2] == "refresh" and "ID" in params:
                    return self.catalog.refreshItem(uri[1], params["ID"])
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            return cherrypy.HTTPError(e.code, e.message)
        except:
            return cherrypy.HTTPError(500, "Internal Server Error.")

    def DELETE(self, *uri, **params):
        pass

if __name__ == "__main__":
    settings = json.load(open("ResourceCatalogSettings.json"))


    port = settings["IPport"]

    Service_info = ServiceInfo(settings["serviceName"], IPport=port)
    ServiceCatalog_url = settings["ServiceCatalog_url"]
    Catalog = RESTResourceCatalog(Service_info, ServiceCatalog_url)
    
    ip_address = socket.gethostbyname(socket.gethostname())

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(Catalog, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        Catalog.Thread.stop()
        cherrypy.engine.block()
        Catalog.catalog.save()
        print("Server stopped")