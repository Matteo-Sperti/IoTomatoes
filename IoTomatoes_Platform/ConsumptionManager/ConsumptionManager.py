import time
import json
import signal
import requests

from iotomatoes_supportpackage import BaseService
import iotomatoes_supportpackage.DeviceManager as DM


class ConsumptionManager (BaseService):
    def __init__(self, settings):
        """Initialize the ConsumptionManager class"""

        super().__init__(settings)
        self._message = {
            'bn': self.EndpointInfo['serviceName'],
            'cn': "",
            'msgType': '',
            'msg': "",
            't': ""
        }
        self.resourceManagerToCall = settings['ResourceManager_ServiceName']
        self.deviceList = []
        self.updateDeviceList()

    def updateDeviceList(self):
        """Get the list of actuators"""

        resourceManager_url = self.getOtherServiceURL(
            self.resourceManagerToCall)
        if resourceManager_url == None or resourceManager_url == "":
            print("ERROR: resource manager service not found!")
            return

        try:
            status_data = requests.get(
                f'{resourceManager_url}/checkActuatorUpdates')
            status = status_data.json()['status']
            if status == True:
                devices_data = requests.get(
                    f'{resourceManager_url}/getActuators')
                new_deviceList = devices_data.json()
                self.deviceList = new_deviceList
        except:
            print("ERROR: resource manager service not available!")

    def updateConsumption(self):
        """Calculate the consumption of the actuators for the passed hour and update the database"""

        totalConsumption = {}
        for dev in self.deviceList:
            if (dev['status'] == 'OFF' and dev['control']):
                dev_consumption = {
                    'cn': dev['CompanyName'],
                    'bn': self.serviceName,
                    'fieldNumber': dev['fieldNumber'],
                    'e': {
                        'n': 'consumption',
                        'v': dev['Consumption_kWh'],
                        'u': 'kWh',
                        'power': dev['PowerConsumption_kW'],
                        't': time.time()
                    }
                }
                if dev['CompanyName'] in totalConsumption:
                    totalConsumption[dev['CompanyName']
                                     ] += dev['Consumption_kWh']
                else:
                    totalConsumption[dev['CompanyName']
                                     ] = dev['Consumption_kWh']
                dev['Consumption_kWh'] = 0
                self._MQTTClient.myPublish(
                    f"{dev['CompanyName']}/{dev['fieldNumber']}/{dev['ID']}/consumption", dev_consumption)

            elif (dev['status'] == 'ON' and dev['control']):
                dev['Consumption_kWh'] = round(
                    (time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600, 2)
                dev_consumption = {
                    'cn': dev['CompanyName'],
                    'bn': self.serviceName,
                    'fieldNumber': dev['fieldNumber'],
                    'e': {
                        'n': 'consumption',
                        'v': dev['Consumption_kWh'],
                        'u': 'kWh',
                        'power': dev['PowerConsumption_kW'],
                        't': time.time()
                    }
                }
                if dev['CompanyName'] in totalConsumption:
                    totalConsumption[dev['CompanyName']
                                     ] += dev['Consumption_kWh']
                else:
                    totalConsumption[dev['CompanyName']
                                     ] = dev['Consumption_kWh']
                dev['OnTime'] = time.time()
                dev['Consumption_kWh'] = 0
                self._MQTTClient.myPublish(
                    f"{dev['CompanyName']}/{dev['fieldNumber']}/{dev['ID']}/consumption", dev_consumption)

        for CompanyName in totalConsumption:
            message = {
                'cn': CompanyName,
                'bn': self.serviceName,
                'tot_consumption': totalConsumption[CompanyName]
            }
            self._MQTTClient.myPublish(
                f"{CompanyName}/Consumption", message)

    def updateStatus(self, actuatorID: int, command: str):
        """Update the status of the actuator, if it is turned OFF calculates its consumption.

        Arguments:
        - `actuatorID (str)` : ID of the actuator
        - `command (str)` : Command sent to the actuator
        """
        for dev in self.deviceList:
            if dev['ID'] == actuatorID:
                if command == 1:
                    dev['status'] = 'ON'
                    dev['OnTime'] = time.time()
                    dev['control'] = True
                    return DM.CheckResult(is_error=False)
                elif command == 0:
                    dev['status'] = 'OFF'
                    # Calculate the consumption of a actuator by its mean power consumption and the time it was on
                    dev['Consumption_kWh'] += round(
                        (time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600, 2)
                    dev['OnTime'] = 0
                    return DM.CheckResult(is_error=False)
                else:
                    return DM.CheckResult(is_error=True, messageType="Error", message="Command not recognized")
        return DM.CheckResult(is_error=True, messageType="Error", message="Actuator not found.")

    def notify(self, topic, payload):
        """Parse the message received and control the topic

        Subscribed topics format:
        - IoTomatoes/CompanyName/Field/ActuatorID/actuatorType
        """
        topic_list = topic.split('/')
        ActuatorID = int(topic_list[-2])
        CompanyName = topic_list[-4]
        try:
            command = payload['e'][-1]['v']
        except:
            msg = self._message.copy()
            msg['cn'] = CompanyName
            msg['msg'] = "Error in the payload"
            msg['msgType'] = "Error"
            msg['t'] = time.time()
            self._MQTTClient.myPublish(
                f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
        else:
            self.updateDeviceList()
            check_actuator = DM.inList(ActuatorID, self.deviceList)
            if check_actuator.is_error:
                msg = self._message.copy()
                msg['cn'] = CompanyName
                msg['msg'] = check_actuator.message
                msg['msgType'] = check_actuator.messageType
                msg['t'] = time.time()
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
            else:
                self.updateStatus(ActuatorID, command)


def sigterm_handler(signal, frame):
    """Handler for the SIGTERM signal, stops the ConsumptionManager"""

    global run
    run = False
    cm.stop()
    print("ConsumptionManager stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open('ConsumptionManagerSettings.json', 'r'))
        ControlPeriod = settings['ControlPeriod']
        cm = ConsumptionManager(settings)
    except Exception as e:
        print(e)
        print("Error, ConsumptionManager not initialized")
    else:
        run = True
        while run:
            cm.updateConsumption()
            time.sleep(ControlPeriod)
