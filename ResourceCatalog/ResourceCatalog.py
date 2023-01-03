import json
import cherrypy
import socket
import sys
sys.path.append("../GenericClasses/")

from CatalogManager import *
from GenericEndPoints import GenericService
from customExceptions import *
from ItemInfo import ServiceInfo

IDperCompany = 10000

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