import time
import json
import signal
import cherrypy

from iotomatoes_supportpackage import BaseService, setREST

keys_to_ignore = ['CompanyName', 'status', 'OnTime',
                  'control', 'Consumption_kWh', 'lastMeasure', 'lastUpdate']


class ResourceManager(BaseService):
    exposed = True

    def __init__(self, settings: dict):
        """Initialize the ResourceManager class"""

        super().__init__(settings)
        self._message = {
            'bn': self.EndpointInfo['serviceName'],
            'cn': "",
            'msgType': '',
            'msg': "",
            't': ""
        }
        self.deviceList = []
        self.checkUpdates()

    def checkUpdates(self):
        """Check if there are changes in the ResourceCatalog and update the device list"""

        new_companyList = self.getCompaniesList()
        new_deviceList = self.createDeviceList(new_companyList)
        if new_deviceList != self.deviceList:
            self.ActuatorsStatus = True
            self.SensorsStatus = True
            self.compareLists(new_deviceList)
        else:
            self.ActuatorsStatus = False
            self.SensorsStatus = False

    def compareLists(self, new_deviceList: list):
        """If there are changes in the device list, update the old list and 
        notify the company"""

        for new_dev in new_deviceList:
            old_dev_iter = filter(lambda d: d.get(
                'ID') == new_dev['ID'], self.deviceList)

            not_present = True
            for d in old_dev_iter:
                not_present = False
                if _different_dicts(d, new_dev, keys_to_ignore):
                    for key in keys_to_ignore:
                        new_dev[key] = d[key]
                    d.update(new_dev)
                    payload = self._message.copy()
                    payload['cn'] = new_dev['CompanyName']
                    payload['msg'] = f"Device {new_dev['ID']} updated."
                    payload['msgType'] = 'Update'
                    payload['t'] = time.time()
                    self._MQTTClient.myPublish(
                        f"{new_dev['CompanyName']}/{self._MQTTClient.publishedTopics[0]}", payload)

            if not_present:
                self.deviceList.append(new_dev)
                payload = self._message.copy()
                payload['cn'] = new_dev['CompanyName']
                payload['msg'] = f"Device {new_dev['ID']} added."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                self._MQTTClient.myPublish(
                    f"{new_dev['CompanyName']}/{self._MQTTClient.publishedTopics[0]}", payload)

        for old_dev in self.deviceList:
            if old_dev['ID'] not in [d['ID'] for d in new_deviceList]:
                self.deviceList.remove(old_dev)
                payload = self._message.copy()
                payload['cn'] = old_dev['CompanyName']
                payload['msg'] = f"Device {old_dev['ID']} removed."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                self._MQTTClient.myPublish(
                    f"{old_dev['CompanyName']}/{self._MQTTClient.publishedTopics[0]}", payload)

    def createDeviceList(self, companyList: list):
        """Create a list of all devices integrating informations about 
        the last time a message was received from a device.

        Arguments:
        - `companyList (list of dict)`: List of all companies and their devices.

        Return:
        - `deviceList (list of dict)`: List of all devices updated
        """

        deviceList = []
        for comp in companyList:
            for dev in comp['devicesList']:
                if dev['isActuator'] and not dev['isSensor']:
                    deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                                'status': 'OFF',
                                                'OnTime': 0,
                                                'control': False,
                                                'Consumption_kWh': 0}})
                elif dev['isSensor'] and not dev['isActuator']:
                    deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                                'lastMeasure': None}})
                elif dev['isActuator'] and dev['isSensor']:
                    deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                                'lastMeasure': None,
                                                'status': 'OFF',
                                                'OnTime': 0,
                                                'control': False,
                                                'Consumption_kWh': 0}})
        return deviceList

    @property
    def ActuatorsStatus(self):
        """Get the status of the Actuators"""

        return self._ActuatorsStatus

    @ActuatorsStatus.setter
    def ActuatorsStatus(self, value: bool):
        """Set the status of the Actuators"""

        self._ActuatorsStatus = value

    @property
    def SensorsStatus(self):
        """Get the status of the Sensors"""

        return self._SensorsStatus
    
    @SensorsStatus.setter
    def SensorsStatus(self, value: bool):
        """Set the status of the Sensors"""

        self._SensorsStatus = value
    
    @property
    def SensorsList(self):
        """Get the list of all sensors"""

        return [dev for dev in self.deviceList if dev['isSensor']]
    
    @property
    def ActuatorsList(self):
        """Get the list of all actuators"""

        return [dev for dev in self.deviceList if dev['isActuator']]

    def GET(self, *uri, **params):
        """GET method for the REST API"""

        if len(uri) != 1:
            raise cherrypy.HTTPError(
                404, "Please specify the service you want to use")
        else:
            if uri[0] == "checkActuatorUpdates":
                return json.dumps({'status': self.ActuatorsStatus})
            elif uri[0] == "checkSensorUpdates":
                return json.dumps({'status': self.SensorsStatus})
            elif uri[0] == "getActuators":
                self.ActuatorsStatus = False
                return json.dumps(self.ActuatorsList)
            elif uri[0] == "getSensors":
                self.SensorsStatus = False
                return json.dumps(self.SensorsList)
            else:
                raise cherrypy.HTTPError(404, "Wrong URL")

def _different_dicts(dict1, dict2, keys_to_ignore):
    """Check if two dictionaries are different"""

    dict1_filtered = {k: v for k,
                      v in dict1.items() if k not in keys_to_ignore}
    dict2_filtered = {k: v for k,
                      v in dict2.items() if k not in keys_to_ignore}

    return dict1_filtered != dict2_filtered


def sigterm_handler(signal, frame):
    """Stop the server when a SIGTERM signal is received"""

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
