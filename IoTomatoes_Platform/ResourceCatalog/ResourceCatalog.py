import json
import time
import cherrypy
import signal

from iotomatoes_supportpackage import BaseService, web_exception, InfoException
from iotomatoes_supportpackage.ItemInfo import (
    constructResource, publishedTopics, setREST)
from iotomatoes_supportpackage.MyIDGenerator import IDs
from iotomatoes_supportpackage.MyThread import MyThread

companyList_name = "companiesList"
devicesList_name = "devicesList"
usersList_name = "usersList"
fieldsList_name = "fieldsList"


class ResourceCatalogManager():
    def __init__(self, heading: dict, filename="CompanyCatalog.json", autoDeleteTime: int = 120,
                 IDs=IDs(100)):
        """Initialize the catalog manager.

        Arguments: 
        - `heading (dict)`: the heading of the catalog. 
        - `filename (str)`: the name of the file where the catalog is saved. 
        - `autoDeleteTime (int)`: the time in seconds between two auto delete of the items. 
        - `IDs (IDs)`: the IDs generator. Default is all integers from 100.
        """
        self.catalog = heading.copy()
        self.catalog["lastUpdate"] = time.time()
        self.catalog[companyList_name] = []

        self._filename = filename
        self._IDs = IDs
        self._autoDeleteTime = autoDeleteTime
        self._autoDeleteItemsThread = MyThread(
            self.autoDeleteItems, interval=self._autoDeleteTime)

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

    def findCompany(self, CompanyName: str):
        """Return the pointer to the company specified in `CompanyInfo`.

        Arguments: 
        - `CompanyName (str)`: the name of the company to find.
        """

        for company in self.catalog[companyList_name]:
            if company["CompanyName"] == CompanyName:
                return company
        return None

    def find_list(self, CompanyName: str, IDvalue: int):
        """Return the list where the item with the ID `IDvalue` is present.

        Arguments:  
        - `CompanyName (str)`: the name of the company to find. 
        - `IDvalue (int)`: the ID of the item to find.
        """

        company = self.findCompany(CompanyName)
        if company != None:
            for key in [usersList_name, devicesList_name]:
                for item in company[key]:
                    if item["ID"] == IDvalue:
                        return company[key]
        return None

    def find_item(self, CompanyName: str, IDvalue: int):
        """Return the item with the ID `IDvalue`.

        Arguments: 
        - `CompanyName (str)`: the name of the company to find. 
        - `IDvalue (int)`: the ID of the item to find.
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

    def getList(self, CompanyName: str, listName: str):
        """Return the list of items of the company specified in `CompanyInfo` in json format.

        Arguments:  
        - `CompanyName (str)`: the name of the company to find. 
        - `listName (str)`: the name of the list to return.
        """

        company = self.findCompany(CompanyName)
        if company != None:
            return json.dumps(company[listName], indent=4)
        raise web_exception(404, "Company not found")

    def getTopics(self, CompanyName: str, params: dict):
        """Return the list of topics of the company `CompanyName` in json format.

        Arguments:  
        - `CompanyName (str)`: the name of the company to find. 
        - `params (dict)`: the parameters to filter the topics.
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(404, "Company not found")
        else:
            outlist = []
            for item in company[devicesList_name]:
                if "fieldNumber" in params:
                    if item["fieldNumber"] != params["fieldNumber"]:
                        outlist.append(publishedTopics(item))
            return json.dumps(outlist, indent=4)

    def getLocation(self, CompanyName: str):
        """Return the location of the company `CompanyName` in json format."""

        item = self.findCompany(CompanyName)
        if item != None:
            return json.dumps({"Location": item["Location"]}, indent=4)
        raise web_exception(404, "Company not found")

    def isRegistered(self, **params):
        """Return the name of the company if the `telegramID` is registered, 
            otherwise return an empty string.

        Arguments:  
        - `telegramID (str)`: the telegramID to find.
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

    def findUserByTelegramID(self, telegramID: str):
        """Return the name of the company if the `telegramID` is registered,
            otherwise return `None`.

        Arguments:  
        - `telegramID (str)` -- the telegramID to find.
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

    def insertCompany(self, **kwargs):
        """Insert a new company in the catalog.

        Arguments: 
        - `CompanyInfo (dict)`: the information about the company.
        - `AdminInfo (dict)`: the information about the admin of the company.
        - `Fieldlist (dict)`: the list of fields of the company. 

        Return: 
        JSON with the status of the operation.
        """
        try:
            CompanyInfo = kwargs["CompanyInfo"]
            AdminInfo = kwargs["AdminInfo"]
            Fieldlist = kwargs["fieldsList"]
        except:
            raise web_exception(
                400, "Missing CompanyInfo, AdminInfo or fieldsList")

        if "CompanyName" not in CompanyInfo:
            raise web_exception(400, "Missing CompanyName")

        out = {}
        if self.findCompany(CompanyInfo["CompanyName"]) != None:
            out["Status"] = False
            out["Error"] = "Company already registered"
        else:
            ID = self._IDs.get_ID()
            AdminID = self._IDs.get_ID()
            if ID == -1 or AdminID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                NewCompany = {
                    "ID": ID,
                    "CompanyName": CompanyInfo["CompanyName"],
                    "Location": CompanyInfo["Location"],
                    "NumberOfFields": int(CompanyInfo["NumberOfFields"]),
                    "adminID": AdminID,
                    usersList_name: [],
                    devicesList_name: [],
                    fieldsList_name: Fieldlist
                }
                new_item = AdminInfo
                new_item["ID"] = AdminID
                new_item["lastUpdate"] = time.time()
                NewCompany[usersList_name].append(new_item)
                self.catalog[companyList_name].append(NewCompany)
                self.catalog["lastUpdate"] = time.time()
                out = {"Status": True,
                       "CompanyID": ID
                       }

        return json.dumps(out, indent=4)

    def insertDevice(self, CompanyName: str, deviceInfo: dict):
        """Insert a new device in the catalog.

        Arguments: 
        - `CompanyName (str)`: the name of the company of the device. 
        - `deviceInfo (dict)`: the information about the device. 
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(404, "No Company found")
        else:
            ID = self._IDs.get_ID()
            if ID == -1:
                raise web_exception(500, "No more IDs available")
            else:
                self.catalog["lastUpdate"] = time.time()
                try:
                    new_item = constructResource(ID, CompanyName, deviceInfo)
                except InfoException as e:
                    raise web_exception(500, e.message)

                if not (new_item["fieldNumber"] >= 0
                        and new_item["fieldNumber"] <= company["NumberOfFields"]):
                    raise web_exception(400, "Field number not valid")
                company[devicesList_name].append(new_item)
                return json.dumps(new_item, indent=4)

    def insertUser(self, CompanyName: str, userInfo: dict):
        """Insert a new user in the catalog.

        Arguments: 
        - `CompanyName (str)`: the name of the company of the user. 
        - `userInfo (dict)`: the information about the user. 

        Return: 
        JSON with the status of the operation.
        """
        company = self.findCompany(CompanyName)
        if company == None:
            raise web_exception(404, "No Company found")

        if "telegramID" not in userInfo:
            raise web_exception(400, "Missing telegramID")
        else:
            NewCompanyName = self.findUserByTelegramID(userInfo["telegramID"])
            if NewCompanyName != None:
                raise web_exception(
                    403, f"User already registered in {NewCompanyName}")

        ID = self._IDs.get_ID()
        if ID == -1:
            raise web_exception(500, "No more IDs available")
        else:
            self.catalog["lastUpdate"] = time.time()
            new_item = userInfo
            new_item["ID"] = ID
            new_item["lastUpdate"] = time.time()
            company[usersList_name].append(new_item)
            return json.dumps(new_item, indent=4)

    def updateField(self, CompanyName: str, params: dict):
        """Update a field in the catalog.

        Arguments: 
        - `CompanyName (str)`: the name of the company of the field. 
        - `params (dict)`: the information about the field. 

        Return: 
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

    def deleteCompany(self, dict_info: dict):
        """Delete a company from the catalog. """

        if "CompanyName" not in dict_info:
            raise web_exception(400, "Missing CompanyName")

        if "telegramID" not in dict_info:
            raise web_exception(400, "Missing telegramID")
        try:
            chatID = int(dict_info["telegramID"])
        except ValueError:
            raise web_exception(400, "Invalid telegramID")

        company = self.findCompany(dict_info["CompanyName"])
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
                    raise web_exception(
                        403, "You are not the admin of this company")

        raise web_exception(403, "You are not a user of this company")

    def refreshItem(self, CompanyName: str, IDvalue: int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Arguments:
        - `CompanyName (str)`: the name of the company of the device. 
        - `IDvalue (int)`: the ID of the device. 
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

    def __init__(self, settings: dict):
        """Initialize the REST endpoint.

        Arguments:
        - `settings` is a dictionary with the settings of the endpoint.
        """
        filename = settings["filename"]
        autoDeleteTime = settings["autoDeleteTime"]
        super().__init__(settings)
        self.catalog = ResourceCatalogManager(
            self.EndpointInfo, filename, autoDeleteTime)

    def close(self):
        """Close the endpoint and save the catalog."""

        self.catalog._autoDeleteItemsThread.stop()
        self.catalog.save()
        self.stop()

    def GET(self, *uri, **params):
        """GET method for the REST API.
        Return a json with the requested information.

        Allowed URLs:
        - `/companies` : return the list of all the companies.
        - `/companies/names` : return the list of the names of all the companies.
        - `/<CompanyName>/devices` : return the list of all the devices of the company.
        - `/<CompanyName>/users` : return the list of all the users of the company.
        - `/<CompanyName>/fields` : return the list of all the fields of the company.
        - `/<CompanyName>/location` : return the location of the company.
        - `/isRegistered?telegramID=<telegramID>` : return the 'CompanyName' if the telegramID 
        is already registered in a company, an empty string otherwise.
        - `/<CompanyName>/topics` : return the list of all the topics of the company. In the 
        parameters you can specify the fieldNumber to get the topics of a specific field.

        """
        try:
            if len(uri) == 1 and uri[0] == "isRegistered":
                return self.catalog.isRegistered(**params)
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
            else:
                raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")

    def POST(self, *uri, **params):
        """POST method for the REST API.
        Return a json with the status of the operation.

        Allowed URLs:
        - `/company`: insert a new company in the catalog. 
        The body must contain the company information and the Administrator information.
        - `/<CompanyName>/device`: insert a new device in the catalog. 
        The parameters are the device information.
        - `/<CompanyName>/user`: insert a new user in the catalog. 
        The parameters are the user information.
        """
        try:
            if len(uri) == 1 and uri[0] == "company":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.catalog.insertCompany(**body_dict)
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
        - `/<CompanyName>/refresh`: update the device information. 
        The parameters are `ID`, `CompanyName`.
        - `/<CompanyName>/field`: update the field information. 
        In the parameters must be the field number and the new plant.
        """
        try:
            if len(uri) == 2 and uri[1] == "refresh" and "ID" in params:
                return self.catalog.refreshItem(uri[0], int(params["ID"]))
            elif len(uri) == 2 and uri[1] == "field":
                return self.catalog.updateField(uri[0], params)
            else:
                raise web_exception(404, "Resource not found.")
        except web_exception as e:
            return cherrypy.HTTPError(e.code, e.message)
        except:
            return cherrypy.HTTPError(500, "Internal Server Error.")

    def DELETE(self, *uri, **params):
        """DELETE method for the REST API.

        Allowed URLs:
        - `/company`: delete the company from the platform. 
        The parameters are `telegramID` and `CompanyName`
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
