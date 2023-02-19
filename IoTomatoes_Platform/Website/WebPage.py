import json
import os
import cherrypy
import signal

from iotomatoes_supportpackage import BaseService, setREST

class WebPage(BaseService):
    exposed = True

    def __init__(self, settings:  dict):
        """ Constructor of the class

        Arguments:
        `settings (dict)`: the settings of the service
        """
        super().__init__(settings)

    def GET(self, *uri, **params):
        return open("index.html")


def sigterm_handler(signal, frame):
    webService.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
    settings = json.load(open("WebPageSettings.json", "r"))

    ip_address, port = setREST(settings)

    print("Starting server...")

    conf = {
        '/' : {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.staticdir.root': os.path.abspath(os.getcwd()),
            },
        '/css' : {
                'tools.staticdir.on' : True,
                'tools.staticdir.dir' : './img'
            }
    }

    webService = WebPage(settings)
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()