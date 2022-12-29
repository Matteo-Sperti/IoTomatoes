import json
import cherrypy
from CatalogManager import CatalogManager
from customExceptions import *

class RESTServiceCatalog(CatalogManager):
    exposed = True

    def __init__(self, settings : dict):
        """ Initialize the RESTServiceCatalog class.

        Keyword arguments:
        ``heading`` is the heading of the catalog
        ``name`` is the name of the catalog
        ``filename`` is the name of the file to save the catalog
        ``autoDeleteTime`` is the time in seconds to delete the services that are not online anymore
        """
        heading = {
            "owner": settings["owner"], 
            "CatalogName": settings["CatalogName"],
            "broker": settings["broker"],
            }

        self.list_name = "servicesList"
        self.base_uri = settings["CatalogName"]
        super().__init__(heading, [self.list_name], settings["filename"], settings["autoDeleteTime"])

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
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "save":
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


if __name__ == "__main__":
    settings = json.load(open("ServiceCatalogSettings.json"))

    ip_address = settings["REST_settings"]["ip_address"]
    port = settings["REST_settings"]["port"]

    Catalog = RESTServiceCatalog(settings)

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