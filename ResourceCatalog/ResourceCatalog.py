import json
import time
import cherrypy
from socket import gethostname, gethostbyname
import sys

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint
from ItemInfo import *
from MyExceptions import *
from MyIDGenerator import IDs
from MyThread import MyThread

companyList_name = "companiesList"
devicesList_name = "devicesList"
usersList_name = "usersList"

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

class ResourceCatalogManager():
    def __init__(self, heading : dict, filename = "CompanyCatalog.json", autoDeleteTime = 120, 
                    IDs = IDs(100)):
        self.catalog = heading.copy()
        self.catalog["lastUpdate"] = time.time()
        self.catalog[companyList_name] = []

        self._filename = filename
        self._IDs = IDs
        self._autoDeleteTime = autoDeleteTime
        self.autoDeleteItemsThread = MyThread(self.autoDeleteItems, interval=self._autoDeleteTime)

    def save(self):
        try:
            fp = open(self._filename, "w")
            json.dump(self.catalog, fp, indent=4)
            fp.close()
        except FileNotFoundError:
            print(f"File {self._filename} not found!")

    def print_catalog(self):
        """Return the catalog in json format."""
        return json.dumps(self.catalog, indent=4)

    def load(self):
        """Load the catalog from the file specified in the initialization."""
        try:
            self.catalog = json.load(open(self._filename, "r"))
            print("Catalog loaded!\n")
            return json.dumps({"Status": True}, indent=4)
        except FileNotFoundError:
            print("Catalog file not found!\n")
            return json.dumps({"Status": False}, indent=4)

    def isAuthorize(self, company : dict, credentials : dict):
        if "CompanyName" not in credentials or "CompanyToken" not in credentials:
            raise web_exception(400, "Missing credentials")

        if company["CompanyName"] == credentials["CompanyName"]:
            if company["CompanyToken"] == credentials["CompanyToken"]:
                return True
            else:
                raise web_exception(401, "Wrong credentials")
        else:
            return False
    
    def findCompany(self, CompanyInfo):
        for company in self.catalog[companyList_name]:
            if self.isAuthorize(company, CompanyInfo):
                return company
        return None

    def find_list(self, CompanyInfo : dict, IDvalue : int):
        """Return the list where the item with the ID ``IDvalue`` is present."""

        company = self.findCompany(CompanyInfo)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return company[key]
        return None

    def find_item(self, CompanyInfo : dict, IDvalue : int) :
        """Return the item with the ID ``IDvalue``."""

        company = self.findCompany(CompanyInfo)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return item
        return None
    
    def insertCompany(self, CompanyInfo : dict, AdminInfo : dict):
        out = {"Status": False}
        if all(key in CompanyInfo for key in ["CompanyName", "CompanyToken"]):
            ID = self._IDs.get_ID()
            AdminID = self._IDs.get_ID()
            if ID == -1 or AdminID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                print(f"New company: {CompanyInfo['CompanyName']}\n"
                        f"CompanyToken: {CompanyInfo['CompanyToken']}\n"
                        f"Admin information: \n"
                        f"{json.dumps(AdminInfo, indent=4)}\n")
                if query_yes_no(f"Are you sure you want to add the company {CompanyInfo['CompanyName']}?"):
                    NewCompany = {
                        "ID": ID,
                        "CompanyName": CompanyInfo["CompanyName"],
                        "CompanyToken": str(CompanyInfo["CompanyToken"]),
                        "adminID": AdminID,
                        usersList_name: [],
                        devicesList_name: []
                    }
                    new_item = AdminInfo
                    new_item["ID"] = AdminID
                    new_item["lastUpdate"] =  time.time()
                    NewCompany[usersList_name].append(new_item)
                    self.catalog[companyList_name].append(NewCompany)
                    self.catalog["lastUpdate"] =  time.time() 
                    out = {"Status": True, "CompanyID": ID, "CompanyToken": CompanyInfo["CompanyToken"]}
        
        return json.dumps(out, indent=4)

    def get_all(self, list_key : str):
        """Return a json with all the items in the list specified in ``list_key``."""
        try:
            return json.dumps(self.catalog[list_key], indent=4)
        except KeyError:
            raise web_exception(404, "List not found")

    def getItem(self, CompanyInfo : dict, ID : int):
        """Return the REST or MQTT information of item ``ID`` in json format.

        Keyword arguments:
        ``info`` is the type of information to return (REST, MQTT) and
        ``ID`` is the ID of the item to return the information of
        """
        item = self.find_item(CompanyInfo, ID)

        if item != None:
            return json.dumps(item, indent=4)
        raise web_exception(404, "Service info not found")

    def getCompany(self, CompanyInfo : dict):
        company = self.findCompany(CompanyInfo)
        if company != None:
            return json.dumps(company, indent=4)
        raise web_exception(404, "Company not found")

    def insertDevice(self, CompanyInfo : dict, deviceInfo : dict):
        company = self.findCompany(CompanyInfo)
        if company != None:
            ID = self._IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] =  time.time() 
                try:
                    new_item = constructResource(ID, CompanyInfo, deviceInfo)
                except InfoException as e:
                    raise web_exception(500, e.message)
                company[devicesList_name].append(new_item)
                out = {"ID": ID}
                return json.dumps(out, indent=4)
        else:
            raise web_exception(500, "No Company found")

    def insertUser(self, CompanyInfo : dict, userInfo : dict):
        company = self.findCompany(CompanyInfo)
        if company != None:
            ID = self._IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] =  time.time() 
                new_item = userInfo
                new_item["ID"] = ID
                new_item["lastUpdate"] =  time.time()
                company[usersList_name].append(new_item)
                out = {"ID": ID}
                return json.dumps(out, indent=4)
        else:
            raise web_exception(500, "No Company found")

    def update(self, CompanyInfo : dict, ID : int, new_item : dict):
        """Update a device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``ID`` is the ID of the item to update and
        ``new_item`` is the item in json format to update
        """

        item = self.find_item(CompanyInfo, ID)
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

    def deleteItem(self, CompanyInfo : dict, IDvalue : int):
        """Delete a item from the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``IDvalue`` is the ID of the item to delete
        """

        current_list = self.find_list(CompanyInfo, IDvalue)
        if current_list != None:
            actualtime = time.time()
            self.catalog["lastUpdate"] = actualtime
            for item in current_list:
                if item["ID"] == IDvalue:
                    current_list.remove(item)
                    self._IDs.free_ID(IDvalue)
                    break
            out = {"Status": True}
        else:
            out = {"Status": False}
        return json.dumps(out, indent=4)

    def refreshItem(self, CompanyInfo : dict, IDvalue : int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Keyword arguments:
        ``IDvalue`` is the ID of the item to refresh
        """

        item = self.find_item(CompanyInfo, IDvalue)
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
        for company in self.catalog[companyList_name]:
            for device in company[devicesList_name]:
                try:
                    if actualtime - device["lastUpdate"] > self._autoDeleteTime:
                        self._IDs.free_ID(device["ID"])
                        print(f"""DeviceID : {device["ID"]} removed""")
                        company[devicesList_name].remove(device)
                except KeyError:
                    print("Device without lastUpdate field")
                    company[devicesList_name].remove(device)
        self.catalog["lastUpdate"] = actualtime


class RESTResourceCatalog():
    exposed = True

    def __init__(self, settings : dict): 
        filename = settings["filename"]
        autoDeleteTime = settings["autoDeleteTime"]
        self.Service = GenericEndpoint(settings, isService=True)
        self.catalog = ResourceCatalogManager(self.Service._EndpointInfo, filename, autoDeleteTime)

    def close(self):
        self.catalog.autoDeleteItemsThread.stop()
        self.catalog.save()
        self.Service.stop()

    def GET(self, *uri, **params):
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "getCompany":
                    if all(key in params for key in ["CompanyName", "CompanyToken"]):
                        CompanyInfo = {"CompanyName": params["CompanyName"], "CompanyToken": params["CompanyToken"]}
                        return self.catalog.getCompany(CompanyInfo)
                elif len(uri) == 1 and uri[0] == "get":
                    if all(key in params for key in ["ID", "CompanyName", "CompanyToken"]):
                        CompanyInfo = {"CompanyName": params["CompanyName"], "CompanyToken": params["CompanyToken"]}
                        return self.catalog.getItem(CompanyInfo, int(params["ID"]))
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")

    def POST(self, *uri, **params):
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "insertCompany":
                    body_dict = json.loads(cherrypy.request.body.read())
                    return self.catalog.insertCompany(params, body_dict)
                elif len(uri) == 2 and uri [0] == "insert":
                    body_dict = json.loads(cherrypy.request.body.read())
                    if uri[1] == "user":
                        return self.catalog.insertUser(params, body_dict)
                    elif uri[1] == "device":
                        return self.catalog.insertDevice(params, body_dict)
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error.")
    
    def PUT(self, *uri, **params):
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "refresh":
                    if all(key in params for key in ["ID", "CompanyName", "CompanyToken"]):
                        CompanyInfo = {"CompanyName": params["CompanyName"], "CompanyToken": params["CompanyToken"]}
                        return self.catalog.refreshItem(CompanyInfo, int(params["ID"]))
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            return cherrypy.HTTPError(e.code, e.message)
        except:
            return cherrypy.HTTPError(500, "Internal Server Error.")

    def DELETE(self, *uri, **params):
        pass

if __name__ == "__main__":
    settings = json.load(open("ResourceCatalogSettings.json"))

    ip_address = gethostbyname(gethostname())
    port = settings["IPport"]
    settings["IPaddress"] = ip_address

    try:
        Catalog = RESTResourceCatalog(settings)
    except InfoException as e:
        print(e.message)
    except KeyError as e:
        print(e)
        print("KeyError, Error while creating the catalog")
    except:
        print("Error while creating the catalog")
    else:
        Catalog.Service.start()
        
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
            Catalog.close()
            print("Catalog closed, press Ctrl+C to stop the server")
            cherrypy.engine.block()
            print("Server stopped")