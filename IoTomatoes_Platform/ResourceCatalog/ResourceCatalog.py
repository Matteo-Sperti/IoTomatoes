import json
import time
import cherrypy
import signal

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception, InfoException
from iotomatoes_supportpackage.ItemInfo import (
    constructResource, measureType, actuatorType, publishedTopics, setREST)
from iotomatoes_supportpackage.MyIDGenerator import IDs
from iotomatoes_supportpackage.MyThread import MyThread

companyList_name = "companiesList"
devicesList_name = "devicesList"
usersList_name = "usersList"
fieldsList_name = "fieldsList"

class ResourceCatalogManager():
    def __init__(self, heading : dict, filename = "CompanyCatalog.json", autoDeleteTime = 120, 
                    IDs = IDs(100)):
        """Initialize the catalog manager.
    
        Arguments:\n
        `heading (dict)`: the heading of the catalog.\n
        `filename (str)`: the name of the file where the catalog is saved.\n
        `autoDeleteTime (int)`: the time in seconds between two auto delete of the items.\n
        `IDs (IDs)`: the IDs generator. Default is all integers from 100.
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

        if "CompanyName" not in credentials:
            raise web_exception(400, "Missing credentials")

        if company["CompanyName"] == credentials["CompanyName"]:
            if "CompanyToken" in credentials:
                if company["CompanyToken"] == credentials["CompanyToken"]:
                    return True
                else:
                    raise web_exception(401, "Wrong credentials")
            else:
                return False
        else:
            return False
    
    def findCompany(self, CompanyName : str):
        """Return the pointer to the company specified in `CompanyInfo`.
        
        Arguments:\n
        `CompanyName (str)`: the name of the company to find.
        """

        for company in self.catalog[companyList_name]:
            if company["CompanyName"] == CompanyName:
                return company
        return None

    def find_list(self, CompanyName : str, IDvalue : int):
        """Return the list where the item with the ID `IDvalue` is present.
        `CompanyName (str)`: the name of the company to find.
        """

        company = self.findCompany(CompanyName)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return company[key]
        return None

    def find_item(self, CompanyName : str, IDvalue : int) :
        """Return the item with the ID `IDvalue`.
        `CompanyName` -- the name of the company to find.
        """

        company = self.findCompany(CompanyName)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return item
        return None
    
    def getAll(self):
        """Return a json with the list of all the companies in the catalog."""

        return json.dumps(self.catalog[companyList_name], indent=4)

    def getCompanyNameList(self):
        """Return a json with the list of names of all the companies in the catalog."""

        return json.dumps([company["CompanyName"] for company in self.catalog[companyList_name]], indent=4)

    def getList(self, CompanyName : str, listName : str):
        """Return the list of items of the company specified in `CompanyInfo` in json format.

        Arguments: \n
        `CompanyName (str)`: the name of the company to find.\n
        `listName (str)`: the name of the list to return.
        """

        company = self.findCompany(CompanyName)
        if company != None:
            return json.dumps(company[listName], indent=4)
        raise web_exception(404, "Company not found")

    def getTopics(self, CompanyName : str, params : dict):
        """Return the list of topics of the company `CompanyName` in json format.

        Arguments: \n
        `CompanyName (str)`: the name of the company to find.\n
        `params (dict)`: the parameters to filter the topics.
        """
        company = self.findCompany(CompanyName)
        if company != None:
            for item in company[devicesList_name]:
                if item["field"] == field:
                    if ResourceType in measureType(item) or ResourceType in actuatorType(item):
                        return json.dumps(publishedTopics(item), indent=4)
        raise web_exception(404, "Company not found")


    def getLocation(self, CompanyName : str):
        """Return the location of the company `CompanyName` in json format."""

        item = self.findCompany(CompanyName)
        if item != None:
            return json.dumps({"Location": item["Location"]}, indent=4)
        raise web_exception(404, "Service info not found")

    def isRegistered(self, params : dict):
        """Return the name of the company if the `telegramID` is registered, 
            otherwise return an empty string.

        Arguments: \n
        `params (dict)`: must contain the  `telegramID`.
        """
        
        out = {"CompanyName": ""}
        if "telegramID" not in params:
            raise web_exception(400, "Missing telegramID")
        else:
            CompanyName = self.findUserByTelegramID(params["telegramID"])
            if CompanyName != None:
                out["CompanyName"] = CompanyName
                return json.dumps(out, indent=4)
            else:
                out["CompanyName"] = ""
                return json.dumps(out, indent=4)

    def findUserByTelegramID(self, telegramID : str):
        """Return the name of the company if the `telegramID` is registered,
            otherwise return `None`.

        Arguments: \n
        `telegramID (str)` -- the telegramID to find.
        """

        try:
            chatID = int(telegramID)
        except:
            return None

        for company in self.catalog[companyList_name]:
            for user in company[usersList_name]:
                if user["telegramID"] == chatID:
                    return company["CompanyName"]
        return None

    def insertCompany(self, Info : dict):
        """Insert a new company in the catalog.

        Arguments:\n
        `Info (dict)`: the information about the company.
        Must contain the `CompanyInfo (dict)`: the information about the company.
        `AdminInfo (dict)`: the information about the admin of the company.
        `Fieldlist (dict)`: the list of fields of the company.\n

        Return:\n
        JSON with the status of the operation.
        """
        try:
            CompanyInfo = Info["CompanyInfo"]
            AdminInfo = Info["AdminInfo"]
            Fieldlist = Info["fieldsList"]
        except:
            raise web_exception(400, "Missing CompanyInfo, AdminInfo or fieldsList")

        out = {}
        if self.findCompany(CompanyInfo) != None:
            out["Status"] = False
            out["Error"] = "Company already registered"
        else:
            if all(key in CompanyInfo for key in ["CompanyName", "CompanyToken"]):
                ID = self._IDs.get_ID()
                AdminID = self._IDs.get_ID()
                if ID == -1 or AdminID == -1:
                    raise web_exception(500, "No more IDs available")
                else:
                    NewCompany = {
                        "ID": ID,
                        "CompanyName": CompanyInfo["CompanyName"],
                        "CompanyToken": str(CompanyInfo["CompanyToken"]),
                        "Location": CompanyInfo["Location"],
                        "NumberOfFields" : int(CompanyInfo["NumberOfFields"]),
                        "adminID": AdminID,
                        usersList_name: [],
                        devicesList_name: [],
                        fieldsList_name: Fieldlist
                    }
                    new_item = AdminInfo
                    new_item["ID"] = AdminID
                    new_item["lastUpdate"] =  time.time()
                    NewCompany[usersList_name].append(new_item)
                    self.catalog[companyList_name].append(NewCompany)
                    self.catalog["lastUpdate"] =  time.time() 
                    out = {"Status": True, "CompanyID": ID, "CompanyToken": CompanyInfo["CompanyToken"]}
        
        return json.dumps(out, indent=4)

    def insertDevice(self, CompanyName : str, deviceInfo : dict):
        """Insert a new device in the catalog.

        Arguments:\n
        `CompanyName (str)`: the name of the company of the device.\n
        `deviceInfo (dict)`: the information about the device.\n
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(500, "No Company found")
        else:
            ID = self._IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] =  time.time() 
                try:
                    new_item = constructResource(ID, CompanyName, deviceInfo)
                except InfoException as e:
                    raise web_exception(500, e.message)

                if not (new_item["field"] > 0 and new_item["field"] <= company["NumberOfFields"]) :
                    raise web_exception(400, "Field number not valid")
                company[devicesList_name].append(new_item)
                return json.dumps(new_item, indent=4)

    def insertUser(self, CompanyName : str, userInfo : dict):
        """Insert a new user in the catalog.

        Arguments:\n
        `CompanyName (str)`: the name of the company of the user.\n
        `userInfo (dict)`: the information about the user.\n

        Return:\n
        JSON with the status of the operation.
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(500, "No Company found")

        if "telegramID" not in userInfo:
            raise web_exception(400, "Missing telegramID")

        CompanyName = self.findUserByTelegramID(userInfo["telegramID"])
        if CompanyName != None:
            raise web_exception(403, f"User already registered in {CompanyName}")

        ID = self._IDs.get_ID()
        if ID == -1:
            raise web_exception(500, "No more IDs available")
        else:
            self.catalog["lastUpdate"] =  time.time() 
            new_item = userInfo
            new_item["ID"] = ID
            new_item["lastUpdate"] =  time.time()
            company[usersList_name].append(new_item)
            return json.dumps(new_item, indent=4)


    def updateField(self, CompanyName : str, params : dict) : 
        """Update a field in the catalog.

        Arguments:\n
        `CompanyName (str)`: the name of the company of the field.\n
        `params (dict)`: the information about the field.\n

        Return:\n
        JSON with the status of the operation.
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(404, "No Company found")
        
        if "fieldNumber" not in params or "plant" not in params:
            raise web_exception(400, "Missing fieldNumber or plant")
        
        try:
            fieldNumber = int(params["fieldNumber"])
        except ValueError:
            raise web_exception(400, "fieldNumber must be an integer")

        for field in company[fieldsList_name]:
            if field["fieldNumber"] == fieldNumber:
                field["plant"] = params["plant"]
                self.catalog["lastUpdate"] = time.time()
                return json.dumps({"Status": True}, indent=4)

        raise web_exception(404, "Field not found")

    def deleteCompany(self, dict_info : dict):
        """Delete a company from the catalog. """

        if "CompanyName" not in dict_info or "CompanyToken" not in dict_info:
            raise web_exception(400, "Missing CompanyName or CompanyToken")
        else:
            CompanyInfo = {
                "CompanyName": dict_info["CompanyName"],
                "CompanyToken": dict_info["CompanyToken"]
            }

        if "telegramID" not in dict_info:
            raise web_exception(400, "Missing telegramID")
        try:
            chatID = int(dict_info["telegramID"])
        except ValueError:
            raise web_exception(400, "Invalid telegramID")

        company = self.findCompany(CompanyInfo["CompanyName"])
        if company == None:
            raise web_exception(404, "Company not found")

        AdminID = company["adminID"]
        for user in company[usersList_name]:
            if user["telegramID"] == chatID:
                if user["ID"] == AdminID:
                    for device in company[devicesList_name]:
                        self._IDs.free_ID(device["ID"])
                    for user in company[usersList_name]:
                        self._IDs.free_ID(user["ID"])
                    self._IDs.free_ID(company["ID"])
                    self.catalog[companyList_name].remove(company)
                    out = {"Status": True}
                    return json.dumps(out, indent=4)
                else:
                    raise web_exception(403, "You are not the admin of this company")
        
        raise web_exception(403, "You are not a user of this company")

    def refreshItem(self, CompanyName : str, IDvalue : int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Aarguments:
        `CompanyName (str)`: the name of the company of the device.\n
        `IDvalue (int)`: the ID of the device.\n
        """

        item = self.find_item(CompanyName, IDvalue)
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
                        print(f"DeviceID : {device['ID']} removed")
                        company[devicesList_name].remove(device)
                except KeyError:
                    print("Device without lastUpdate field")
                    company[devicesList_name].remove(device)
        self.catalog["lastUpdate"] = actualtime
        self.save()

class RESTResourceCatalog(BaseService):
    exposed = True

    def __init__(self, settings : dict): 
        """Initialize the REST endpoint.

        Arguments:
        `settings` is a dictionary with the settings of the endpoint.
        """
        filename = settings["filename"]
        autoDeleteTime = settings["autoDeleteTime"]
        super().__init__(settings)
        self.catalog = ResourceCatalogManager(self._EndpointInfo, filename, autoDeleteTime)

    def close(self):
        """Close the endpoint and save the catalog."""

        self.catalog.autoDeleteItemsThread.stop()
        self.catalog.save()
        self.stop()

    def GET(self, *uri, **params):
        """GET method for the REST API.
        Return a json with the requested information.
        
        Allowed URLs: \n
        `/companies` : return the list of all the companies.\n
        `/companies/names` : return the list of the names of all the companies.\n
        `/<CompanyName>/devices` : return the list of all the devices of the company.\n
        `/<CompanyName>/users` : return the list of all the users of the company.\n
        `/<CompanyName>/fields` : return the list of all the fields of the company.\n
        `/<CompanyName>/location` : return the location of the company.\n
        `/isRegistered?telegramID=<telegramID>` : return the 'CompanyName' if the telegramID 
        is already registered in a company, an empty string otherwise.\n
        `/<CompanyName>/topics` : return the list of all the topics of the company. In the 
        parameters you can specify the fieldNumber to get the topics of a specific field.\n
        
        """
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "isRegistered":
                    return self.catalog.isRegistered(params)
                elif len(uri) == 1 and uri[0] == "companies":
                    return self.catalog.getAll()
                if len(uri) == 2 and uri[0] == "companies" and uri[1] == "names":
                    return self.catalog.getCompanyNameList()    
                elif len(uri) == 2 and uri[1] == "devices":
                    return self.catalog.getList(uri[0], devicesList_name)
                elif len(uri) == 2 and uri[1] == "users":
                    return self.catalog.getList(uri[0], usersList_name)
                elif len(uri) == 2 and uri[1] == "fields":
                    return self.catalog.getList(uri[0], fieldsList_name)
                elif len(uri) == 2 and uri[1] == "location":
                    return self.catalog.getLocation(uri[0])
                elif len(uri) == 2 and uri[1] == "topics":
                    return self.catalog.getTopics(uri[0], params)

            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")

    def POST(self, *uri, **params):
        """POST method for the REST API.
        Return a json with the status of the operation.
        
        Allowed URLs:
        `/company`: insert a new company in the catalog. 
        The body must contain the company information and the Administrator information.\n
        `/<CompanyName>/device`: insert a new device in the catalog. The parameters are the device information.\n
        `/<CompanyName>/user`: insert a new user in the catalog. The parameters are the user information.\n
        """
        try:
            if len(uri) == 1 and uri[0] == "company":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.catalog.insertCompany(body_dict)
            elif len(uri) == 2:
                body_dict = json.loads(cherrypy.request.body.read())
                if uri[1] == "user":
                        return self.catalog.insertUser(uri[0], body_dict)
                elif uri[1] == "device":
                    return self.catalog.insertDevice(uri[0], body_dict)
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error.")
    
    def PUT(self, *uri, **params):
        """PUT method for the REST API.

        Allowed URLs:
        `/<CompanyName>/refresh`: update the device information. 
        The parameters are `ID`, `CompanyName`.\n
        `/<CompanyName>/field`: update the field information. 
        In the parameters must be the field number and the new plant.\n
        """
        try:
            if len(uri) > 0:
                if len(uri) == 2 and uri[1] == "refresh":
                    if "ID" in params:
                        return self.catalog.refreshItem(uri[0], int(params["ID"]))
                if len(uri) == 2 and uri[1] == "field":
                    return self.catalog.updateField(uri[0], params)
            raise web_exception(404, "Resource not found.")
        except web_exception as e:
            return cherrypy.HTTPError(e.code, e.message)
        except:
            return cherrypy.HTTPError(500, "Internal Server Error.")

    def DELETE(self, *uri, **params):
        """DELETE method for the REST API.

        Allowed URLs:
        `/company`: delete the company from the platform. 
        The parameters are `telegramID`, `CompanyName` and `CompanyToken`.\n
        """

        if len(uri) == 1 and uri[0] == "company":
            try:
                return self.catalog.deleteCompany(params)
            except web_exception as e:
                return cherrypy.HTTPError(e.code, e.message)
            except:
                return cherrypy.HTTPError(500, "Internal Server Error.")

        raise cherrypy.HTTPError(400, "Unrecognized command.")

def sigterm_handler(signal, frame):
    Catalog.close()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")

signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    settings = json.load(open("ResourceCatalogSettings.json", "r"))

    ip_address, port = setREST(settings)

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

        while True:
            time.sleep(5)