import json
import cherrypy
from CatalogManager import RESTServiceCatalog

if __name__ == "__main__":
    settings = json.load(open("ServiceCatalogSettings.json"))

    ip_address = settings["REST_settings"]["ip_address"]
    port = settings["REST_settings"]["port"]

    heading = {
        "projectOwner": settings["owner"], 
        "projectName": settings["projectName"],
        "broker": settings["broker"],
        }

    Catalog = RESTServiceCatalog(heading, settings["filename"], settings["autoDeleteTime"])

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