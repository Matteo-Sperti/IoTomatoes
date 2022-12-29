import json
import cherrypy
import threading
from CatalogManager import *
from GenericEndPoints import GenericService
from customExceptions import *

class RESTResourceCatalog(CatalogManager, GenericService):
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
        self.IDs = IDs(100)
        self.list_name = "CompanyList"
        self.base_uri = settings["serviceName"]
        super().__init__(ServiceInfo, [self.list_name], settings["filename"], settings["autoDeleteTime"])
        self.start_service(ServiceInfo, settings["serviceName"])

    def GET(self, *uri, **params):
        """REST GET method.

        Allowed commands:
        ``/ServiceCatalog/get/<info>?ID=<ID>`` to get a service info by ID
        ``/ServiceCatalog/getall`` to get all the services
        ``/ServiceCatalog/search/<info>?<info>=<value>`` to search a service by info
        """
        try:
            if len(uri) < 2:
                raise web_exception(404, "No command received")
            elif len(uri) == 3 and uri[0] == self.base_uri and uri[1] == "get" and uri[2] in ["REST", "MQTT"]:
                if "ID" in params:
                    return self.get(uri[2], int(params["ID"]))
                else:
                    raise web_exception(400, "Invalid parameter")
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "getall":
                return self.get_all(self.list_name)
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "broker":
                return self.get_broker()
            elif len(uri) == 3 and uri[0] == self.base_uri and uri[1] == "search":
                if uri[2] in params:
                    return self.search(self.list_name, uri[2], params[uri[2]])
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

        Allowed commands:
        ``/ServiceCatalog/update`` to update the catalog:
        The body of the request must contain the new service info in json format
        ``/ServiceCatalog/refresh?ID=<ID>`` to refresh the lastUpdate field of a service by ID
        """
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "update":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.update(int(params["ID"]), body_dict)
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "refresh":
                if "ID" in params:
                    return self.refreshItem(int(params["ID"]))
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
        
        Allowed commands:
        ``/ServiceCatalog/save`` to save the catalog in the file
        ``/ServiceCatalog/insert`` to insert a new service in the catalog. 
        The body of the request must contain the new service info
        """
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "insertCompany":
                return self.insertCompany(params)
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "save":
                return self.save()
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "insert":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.insert(self.list_name, body_dict)
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

        Allowed commands:
        ``/ServiceCatalog/delete?ID=<ID>`` to delete a service by ID
        """
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "delete":
                if "ID" in params:
                    return self.delete(int(params["ID"]))
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
    
    def insertCompany(self, params):
        if "name" in params:
            ID = self.IDs.get_ID()
            if ID != -1:
                NewCompany = {
                    "ID": ID,
                    "name": params["name"],
                    "adminID": 1,
                    "devicesList": [],
                    "usersList": []
                }
                if query_yes_no(f"Are you sure you want to add the company {params['name']}?"):
                    self.catalog["CompanyList"].append(NewCompany)
                    
                    #inserisci l'utente nella lista degli utenti

        
        return {"Status": False}

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