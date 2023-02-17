import datetime
import time
import json
import signal

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
        companyList = self.getCompaniesList()
        self.deviceList = DM.createDeviceList(companyList, isActuator=True)

    def updateConsumption(self):
        """Calculate the consumption of the actuators for the passed hour and update the database"""

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
                dev['OnTime'] = time.time()
                dev['Consumption_kWh'] = 0
                self._MQTTClient.myPublish(
                    f"{dev['CompanyName']}/{dev['fieldNumber']}/{dev['ID']}/consumption", dev_consumption)

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
            DM.checkUpdate(self, True)
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
    cm.stop()
    print("ConsumptionManager stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open('ConsumptionManagerSettings.json', 'r'))
        cm = ConsumptionManager(settings)
    except Exception as e:
        print(e)
        print("Error, ConsumptionManager not initialized")
    else:
        while True:
            #!To change for testing
            if datetime.datetime.now().second >= 59:  # Update the consumption every hour
                cm.updateConsumption()
            time.sleep(60)
