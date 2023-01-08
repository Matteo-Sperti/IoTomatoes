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
from TerminalQuery import *

companyList_name = "companiesList"
devicesList_name = "devicesList"
usersList_name = "usersList"

class ResourceCatalogManager():
    def __init__(self, heading : dict, filename = "CompanyCatalog.json", autoDeleteTime = 120, 
                    IDs = IDs(100)):
        """Initialize the catalog manager.
    
        Arguments:\n
        `heading` -- the heading of the catalog.\n
        `filename` -- the name of the file where the catalog is saved. \n
        `autoDeleteTime` -- the time in seconds after which the items are 
        deleted from the catalog (default 120 seconds).\n
        `IDs` -- the IDs generator (default integer number > 100).
        """
        self.catalog = heading.copy()
        self.catalog["lastUpdate"] = time.time()
        self.catalog[companyList_name] = []

        self._filename = filename
        self._IDs = IDs
        self._autoDeleteTime = autoDeleteTime
        self.autoDeleteItemsThread = MyThread(self.autoDeleteItems, interval=self._autoDeleteTime)

    def save(self):
        """Save the catalog to the file specified in the initialization."""

        try:
            fp = open(self._filename, "w")
            json.dump(self.catalog, fp, indent=4)
            fp.close()
        except FileNotFoundError:
            print(f"File {self._filename} not found!")

    def print_catalog(self):
        """Return the catalog in json format."""

        return json.dumps(self.catalog, indent=4)

    def isAuthorize(self, company : dict, credentials : dict):
        """Check if the credentials are correct for the company.
        
        Arguments:\n
        `company` -- the company to check.\n
        `credentials` -- the credentials to access the `company`.\n
        
        Return:\n
        `True` if the credentials are correct, `False` if the credential are for different company.
        Raise an exception is the `CompanyToken` is not correct.
        """

        if "CompanyName" not in credentials or not ("CompanyToken" in credentials 
                and "SystemToken" in credentials):
            raise web_exception(400, "Missing credentials")

        if company["CompanyName"] == credentials["CompanyName"]:
            if company["CompanyToken"] == credentials["CompanyToken"]:
                return True
            else:
                raise web_exception(401, "Wrong credentials")
        else:
            return False

    def systemAuthorize(self, credentials : dict):
        """Check if the credentials are correct for the system.
        
        Arguments:\n
        `credentials` -- the credentials to access the system.\n
        
        Return:\n
        `True` if the credentials are correct.
        Raise an exception is the `SystemToken` is not correct.
        """

        if "SystemToken" not in credentials:
            raise web_exception(400, "Missing credentials")

        if self.catalog["SystemToken"] == credentials["SystemToken"]:
            return True
        else:
            raise web_exception(401, "Wrong credentials")

    def accessInfo(self, params : dict):
        """Return the access info of a device.

        Arguments:\n
        `params` -- a dictionary with the parameters of the request.
        Must contain the `CompanyName` and `CompanyToken` or `SystemToken`.\n
        Return:\n
        JSON with the access info of the device, or an error message.
        """
        if "CompanyName" in params:
            if "CompanyToken" in params:
                CompanyInfo = {"CompanyName": params["CompanyName"], "CompanyToken": params["CompanyToken"]}
                return CompanyInfo
            elif "SystemToken" in params:
                CompanyInfo = {"CompanyName": params["CompanyName"], "SystemToken": params["SystemToken"]}
                return CompanyInfo

        raise web_exception(400, "Error in the access information")
    
    def findCompany(self, CompanyInfo):
        """Return the pointer to the company specified in `CompanyInfo`.
        
        Arguments:\n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`."""

        for company in self.catalog[companyList_name]:
            if self.isAuthorize(company, CompanyInfo):
                return company
        return None

    def find_list(self, CompanyInfo : dict, IDvalue : int):
        """Return the list where the item with the ID `IDvalue` is present.
        `CompanyInfo` is used to check if the request is authorized.
        Must contain the `CompanyName` and `CompanyToken`.
        """

        company = self.findCompany(CompanyInfo)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return company[key]
        return None

    def find_item(self, CompanyInfo : dict, IDvalue : int) :
        """Return the item with the ID `IDvalue`.
        `CompanyInfo` is used to check if the request is authorized."""

        company = self.findCompany(CompanyInfo)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return item
        return None
    
    def getAll(self, credential : dict):
        """Return a json with the list of all the companies in the catalog.

        Arguments:\n
        `credential` -- dictionary with `SystemToken`, the token of the system to authorize the request.
        """

        if self.systemAuthorize(credential):
            return json.dumps(self.catalog[companyList_name], indent=4)

    def getCompanyNameList(self, credential : dict):
        """Return a json with the list of names of all the companies in the catalog.

        Arguments:\n
        `credential` -- dictionary with `SystemToken`, the token of the system to authorize the request.
        """

        if self.systemAuthorize(credential):
            return json.dumps([company["CompanyName"] for company in self.catalog[companyList_name]], indent=4)

    def getItem(self, CompanyInfo : dict, ID : int):
        """Return the information of item `ID` in json format.

        Arguments:
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.\n
        `ID` -- the ID of the item.
        """
        item = self.find_item(CompanyInfo, ID)

        if item != None:
            return json.dumps(item, indent=4)
        raise web_exception(404, "Service info not found")

    def getCompany(self, CompanyInfo : dict):
        """Return the information of the company specified in `CompanyInfo` in json format.

        Arguments:
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.
        """
        company = self.findCompany(CompanyInfo)
        if company != None:
            return json.dumps(company, indent=4)
        raise web_exception(404, "Company not found")

    def getDevices(self, CompanyInfo : dict):
        """Return the list of devices of the company specified in `CompanyInfo` in json format.

        Arguments: \n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.
        """
        company = self.findCompany(CompanyInfo)
        if company != None:
            return json.dumps(company[devicesList_name], indent=4)
        raise web_exception(404, "Company not found")

    def getUsers(self, CompanyInfo : dict):
        """Return the list of users of the company specified in `CompanyInfo` in json format.

        Arguments: \n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.
        """
        company = self.findCompany(CompanyInfo)
        if company != None:
            return json.dumps(company[usersList_name], indent=4)
        raise web_exception(404, "Company not found")

    def getTopics(self, CompanyInfo : dict, field : str, ResourceType : str):
        """Return the list of topics of the company specified in `CompanyInfo` in json format.

        Arguments: \n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.
        """
        company = self.findCompany(CompanyInfo)
        if company != None:
            for item in company[devicesList_name]:
                if getField(item) == field:
                    if ResourceType in measureType(item) or ResourceType in actuatorType(item):
                        return json.dumps(publishedTopics(item), indent=4)
        raise web_exception(404, "Company not found")

    def insertCompany(self, CompanyInfo : dict, AdminInfo : dict):
        """Insert a new company in the catalog.

        Arguments:\n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.\n
        `AdminInfo` -- the information about the admin of the company.\n

        Return:\n
        JSON with the status of the operation.
        """
        out = {}
        if self.systemAuthorize(CompanyInfo):
            if self.findCompany(CompanyInfo) != None:
                out["Status"] = False
                out["Error"] = "Company already present"
            else:
                if all(key in CompanyInfo for key in ["CompanyName", "CompanyToken"]):
                    ID = self._IDs.get_ID()
                    AdminID = self._IDs.get_ID()
                    if ID == -1 or AdminID == -1:
                        raise web_exception(500, "No more IDs available")
                    else:
                        print(f"\nNew company: {CompanyInfo['CompanyName']}\n"
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
        """Insert a new user in the catalog.

        Arguments:\n
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.\n
        `userInfo` -- the information about the user.\n
        
        Return:\n
        JSON with the ID of the user, or an error message.
        """
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
        
        Arguments:
        `ID` -- ID of the item to update and
        `new_item` -- the item in json format to update
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
        
        Arguments:
        `IDvalue` -- the ID of the item to delete
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

        Aarguments:
        `CompanyInfo` -- the information about the company.
        Must contain the `CompanyName` and `CompanyToken`.\n
        `IDvalue` -- the ID of the item to refresh.\n
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


class RESTResourceCatalog(GenericEndpoint):
    exposed = True

    def __init__(self, settings : dict): 
        """Initialize the REST endpoint.

        Arguments:
        `settings` is a dictionary with the settings of the endpoint.
        """
        filename = settings["filename"]
        autoDeleteTime = settings["autoDeleteTime"]
        super().__init__(settings, isService=True)
        self.catalog = ResourceCatalogManager(self._EndpointInfo, filename, autoDeleteTime)

    def close(self):
        """Close the endpoint and save the catalog."""

        self.catalog.autoDeleteItemsThread.stop()
        self.catalog.save()
        self.stop()

    def GET(self, *uri, **params):
        """GET method for the REST API.
        Return a json with the requested information.
        
        Allowed commands: \n
        `/getCompany`: return the company information. The parameters are `CompanyName` and `CompanyToken`.\n
        `/get`: return the device information. The parameters are `ID`, `CompanyName` and `CompanyToken`.\n
        `/devices`: return the list of devices. The parameters are `CompanyName` and `CompanyToken`.\n
        `/users`: return the list of users. The parameters are `CompanyName` and `CompanyToken`.\n
        `/topics/led`: return the list of led topics. The parameters are `field`,  `CompanyName` and `CompanyToken`.\n
        """
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "getCompany":
                    CompanyInfo = self.catalog.accessInfo(params)
                    return self.catalog.getCompany(CompanyInfo)
                elif len(uri) == 1 and uri[0] == "companiesName":
                    return self.catalog.getCompanyNameList(params)    
                elif len(uri) == 1 and uri[0] == "all":
                    return self.catalog.getAll(params)
                elif len(uri) == 1 and uri[0] == "get":
                    if "ID" in params:
                        CompanyInfo = self.catalog.accessInfo(params)
                        return self.catalog.getItem(CompanyInfo, int(params["ID"]))
                elif len(uri) == 1 and uri[0] == "devices":
                    CompanyInfo = self.catalog.accessInfo(params)
                    return self.catalog.getDevices(CompanyInfo)
                elif len(uri) == 1 and uri[0] == "users":
                    CompanyInfo = self.catalog.accessInfo(params)
                    return self.catalog.getUsers(CompanyInfo)
                elif len(uri) == 2 and uri[0] == "topics":
                    if "field" in params:
                        CompanyInfo = self.catalog.accessInfo(params)
                        return self.catalog.getTopics(CompanyInfo, params["field"], uri[1])

            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")

    def POST(self, *uri, **params):
        """POST method for the REST API.
        Return a json with the status of the operation.
        
        Allowed commands:
        `/insertCompany`: insert a new company in the catalog. 
        The parameters are the company information and the Administrator information.\n
        `/insert/device`: insert a new device in the catalog. The parameters are the device information.\n
        `/insert/user`: insert a new user in the catalog. The parameters are the user information.\n
        """
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
        """PUT method for the REST API.

        Allowed commands:
        `/refresh`: update the device information. 
        The parameters are `ID`, `CompanyName` and `CompanyToken`.\n
        """
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
        """DELETE method for the REST API.

        Allowed commands:
        `/deleteCompany`: delete the company from the platform. 
        The parameters are `telegramID`, `CompanyName` and `CompanyToken`.\n
        """
        pass

if __name__ == "__main__":
    settings = json.load(open("ResourceCatalogSettings.json"))

    ip_address = gethostbyname(gethostname())
    port = settings["IPport"]
    settings["IPaddress"] = ip_address

    try:
        Catalog = RESTResourceCatalog(settings)
    except:
        print("Error while creating the catalog")
    else:        
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