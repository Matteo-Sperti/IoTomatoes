import json
import cherrypy
import threading
from CatalogManager import *
from GenericEndPoints import GenericService
from customExceptions import *

IDperCompany = 10000

class CompanyCatalog():
    def __init__(self, heading, filename = "CompanyCatalog.json", autoDeleteTime = 120, IDs = IDs(10000, step=IDperCompany)):
        self.heading = heading
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.IDs = IDs
        self.companyList = []

    def insertCompany(self, params):
        if "name" in params:
            ID = self.IDs.get_ID()
            if ID != -1:
                CompanyInfo = {
                    "ID": ID,
                    "name": params["name"],
                    "adminID": 1,
                }
                if query_yes_no(f"Are you sure you want to add the company {params['name']}?"):
                    NewCompany =CatalogManager(CompanyInfo, ["devicesList", "usersList"], autoDeleteTime=self.autoDeleteTime, IDs=IDs(ID+1, ID+IDperCompany-1))
                    NewCompany.insert("usersList", {})
                    self.companyList.append(NewCompany)


                    #inserisci l'utente nella lista degli utenti

        
        return {"Status": False}



class RESTResourceCatalog(GenericService):
    exposed = True

    def __init__(self, settings : dict):  
        ServiceInfo = {
            "serviceName": settings["serviceName"],
            "owner": settings["owner"],
            "availableServices": [
                "REST"
            ],
            "servicesDetails": [
                {
                    "serviceType": "REST",
                    "serviceIP": f"""{settings["REST_settings"]["ip_address"]}:{settings["REST_settings"]["port"]}"""
                }
            ]
        }
        self.catalog = CompanyCatalog(ServiceInfo, settings["filename"], settings["autodeleteTime"])
        self.base_uri = settings["serviceName"]
        super().__init__(ServiceInfo, settings["serviceName"])

    def GET(self, *uri, **params):
        pass

    def POST(self, *uri, **params):
        pass
    
    def PUT(self, *uri, **params):
        pass

    def DELETE(self, *uri, **params):
        pass

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

if __name__ == "__main__":
    settings = json.load(open("ResourceCatalogSettings.json"))

    ip_address = settings["REST_settings"]["ip_address"]
    port = settings["REST_settings"]["port"]

    Catalog = RESTResourceCatalog(settings)

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

    cherrypy.engine.block()
    Catalog.save()
    print("Server stopped")