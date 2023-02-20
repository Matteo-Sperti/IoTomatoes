import time
import json
import signal
import cherrypy

from iotomatoes_supportpackage import BaseService, setREST
import iotomatoes_supportpackage.DeviceManager as DM


class ResourceManager(BaseService):
    exposed = True

    def __init__(self, settings: dict):
        super().__init__(settings)
        self._message = {
            'bn': self.EndpointInfo['serviceName'],
            'cn': "",
            'msgType': '',
            'msg': "",
            't': ""
        }
        self.ActuatorsStatus = False
        self.SensorsStatus = False
        companyList = self.getCompaniesList()
        self.deviceList = DM.createDeviceList(companyList)

    def checkUpdates(self):
        new_companyList = self.getCompaniesList()
        new_deviceList = DM.createDeviceList(new_companyList)
        if new_deviceList != self.deviceList:
            self.ActuatorsStatus = True
            self.SensorsStatus = True
            DM.compareLists(self, new_deviceList, msg_on=True)
        else:
            self.ActuatorsStatus = False
            self.SensorsStatus = False

    def GET(self, *uri, **params):

        if len(uri) != 1:
            raise cherrypy.HTTPError(
                404, "Please specify the service you want to use")
        else:
            if uri[1] == "checkActuatorUpdates":
                return json.dumps({'status': self.ActuatorsStatus})
            elif uri[1] == "checkSensorUpdates":
                return json.dumps({'status': self.SensorsStatus})
            elif uri[1] == "getActuators":
                self.ActuatorsStatus = False
                return json.dumps(DM.filterList(self.deviceList, 'getActuators'))
            elif uri[1] == "getSensors":
                self.SensorsStatus = False
                return json.dumps(DM.filterList(self.deviceList, 'getSensors'))
            else:
                raise cherrypy.HTTPError(404, "Wrong URL")


def sigterm_handler(signal, frame):
    global run
    run = False
    webService.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Resource manager stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open('ResourceManagerSettings.json', 'r'))
        controlPeriod = settings['ControlPeriod']
    except Exception as e:
        print(e)
        print("Error, ResourceManager not initialized")
    else:
        ip_address, port = setREST(settings)

        print("Starting server...")

        conf = {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True,
            }
        }
        webService = ResourceManager(settings)
        cherrypy.tree.mount(webService, '/', conf)
        cherrypy.config.update({'server.socket_host': ip_address})
        cherrypy.config.update({'server.socket_port': port})
        cherrypy.engine.start()

        run = True
        while run:
            webService.checkUpdates()
            time.sleep(controlPeriod)
