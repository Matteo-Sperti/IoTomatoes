import datetime
import time
import json
import signal
import requests

from iotomatoes_supportpackage import BaseService
import iotomatoes_supportpackage.DeviceManager as DM


class FaultDetector(BaseService):
    def __init__(self, settings):
        """Initialize the FaultDetector class"""

        self.thresholds = settings['thresholds']

        super().__init__(settings)
        self._message = {
            'bn': self.EndpointInfo['serviceName'],
            'cn': '',
            'msgType': '',
            'msg': '',
            't': ''
        }
        self.resourceManagerToCall = settings['ResourceManager_ServiceName']
        resourceManager_url = self.getOtherServiceURL(
            self.resourceManagerToCall)
        if resourceManager_url == None or resourceManager_url == "":
            print("ERROR: resource manager service not found!")
        try:
            devices_data = requests.get(
                f'{resourceManager_url}/getSensors')
            self.deviceList = devices_data.json()
        except:
            print("ERROR: resource manager service not available!")

    def updateStatus(self, deviceID: int):
        """Update the status of a device in the deviceList

        Arguments:
        - `deviceID (int)`: ID of the device to update
        """

        for dev in self.deviceList:
            if dev['ID'] == deviceID:
                dev['lastMeasure'] = datetime.datetime.now()
                break

    def checkStatus(self, device: dict):
        """Check if a device has not sent a message for more than 5 minutes

        Arguments:
        - `device (dict)`: Device to check

        Return: `CheckResult` object with:
        - `error (bool)`: ".is_error"\n
        - `message (str)`: ".message"\n
        - `topic (str)`: ".topic" 
        """

        currentTime = datetime.datetime.now()
        if device['lastMeasure'] is not None:
            elapsedTime = (currentTime - device['lastMeasure']).total_seconds()
            if elapsedTime > 300:
                message = f"Device {device['ID']} has not sent a message for more than 5 minutes, possible fault!"
                return DM.CheckResult(is_error=True, messageType="Warning", message=message,
                                      device_id=device['ID'])
            else:
                return DM.CheckResult(is_error=False)
        return DM.CheckResult(is_error=False)

    def checkMeasure(self, deviceID: int, measureType: str,  measure, unit: str):
        """Check if a measure is out of the thresholds.

        Arguments:\n
        - `deviceID (int)`: ID of the device
        - `measureType (str)`: Type of the measure to check
        - `measure (float)`: Value of the measure to check

        Return: `CheckResult` object with:
        - `error (bool)`: ".is_error"
        - `message (str)`: ".message"
        - `topic (str)`: ".topic" 
        """
        device = None
        if unit != self.thresholds[measureType]['unit']:
            return DM.CheckResult(is_error=True, messageType="Error", message=f"Unit of measure '{unit}' of device {deviceID} not recognized.")

        for dev in self.deviceList:
            if dev['ID'] == deviceID:
                device = dev
                break
        if not device:
            return DM.CheckResult(is_error=True, messageType="Error", message="Device not found")
        if (measureType == 'position'):
            try:
                position_data = requests.get(
                    f"http://{self.ResourceCatalog_url}/{device['CompanyName']}/location")
                max_latitude = position_data.json(
                )['Location']['latitude']+self.thresholds['latitude']['max_value']
                min_latitude = position_data.json(
                )['Location']['latitude']+self.thresholds['latitude']['min_value']
                max_longitude = position_data.json(
                )['Location']['longitude']+self.thresholds['longitude']['max_value']
                min_longitude = position_data.json(
                )['Location']['longitude']+self.thresholds['longitude']['min_value']
            except:
                print("ERROR: resource catalog not available!")
                return DM.CheckResult(is_error=True, messageType="Error", message=f"Position of company {device['CompanyName']} not found.")
            if (measure['latitude'] > max_latitude or measure['latitude'] < min_latitude) or (measure['longitude'] > max_longitude or measure['longitude'] < min_longitude):
                message = (f"Device {deviceID} is out of the defined range, possible fault!\n"
                           f"Value = {measure['latitude']}, {measure['longitude']} {unit}")
                return DM.CheckResult(is_error=True, messageType="Warning", message=message,
                                      device_id=deviceID)
        else:
            if measureType not in device['measureType']:
                return DM.CheckResult(is_error=True, messageType="Error", message=f"Measure type of device {deviceID} not recognized.")

            min_value = self.thresholds[measureType]['min_value']
            max_value = self.thresholds[measureType]['max_value']

            if min_value is None or max_value is None:
                return DM.CheckResult(is_error=True, messageType="Error", message="Thresholds not configured")

            if measure > max_value or measure < min_value:
                message = (f"Device {deviceID} has sent a measure out of the thresholds, possible fault!\n"
                           f"Value = {measure} {unit}")
                return DM.CheckResult(is_error=True, messageType="Warning", message=message,
                                      device_id=deviceID)
        return DM.CheckResult(is_error=False)

    def notify(self, topic, payload):
        """Parse the topic received, check the device status and the measure and publish the alert messages if needed.\n
                Subscribed TOPICS format:\n
                        - CompanyName/Field/DeviceID/MeasureType
        """
        topic_list = topic.split('/')
        measureType = topic_list[-1]
        deviceID = int(topic_list[-2])
        CompanyName = topic_list[-4]
        try:
            measure = payload['e'][-1]['v']
            unit = payload['e'][-1]['u']
        except:
            msg = self._message.copy()
            msg['t'] = time.time()
            msg['cn'] = CompanyName
            msg['msgType'] = "Error"
            msg['msg'] = "Measure not found"
            self._MQTTClient.myPublish(
                f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
        else:
            resourceManager_url = self.getOtherServiceURL(
                self.resourceManagerToCall)
            if resourceManager_url == None or resourceManager_url == "":
                print("ERROR: resource manager service not found!")
            try:
                status_data = requests.get(
                    f'http://{self.resourceManagerToCall}/checkSensorUpdates')
                status = status_data.json()['status']
                if status == True:
                    devices_data = requests.get(
                        f'http://{self.resourceManagerToCall}/getSensors')
                    new_deviceList = devices_data.json()
                    DM.compareLists(self, new_deviceList)
            except:
                print("ERROR: resource manager service not available!")
            sensor_check = DM.inList(deviceID, self.deviceList)
            measure_check = self.checkMeasure(
                deviceID, measureType, measure, unit)
            if sensor_check.is_error:
                msg = self._message.copy()
                msg['t'] = time.time()
                msg['cn'] = CompanyName
                msg['msgType'] = sensor_check.messageType
                msg['msg'] = sensor_check.message
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
            if measure_check.is_error:
                msg = self._message.copy()
                msg['t'] = time.time()
                msg['cn'] = CompanyName
                msg['msgType'] = measure_check.messageType
                msg['msg'] = measure_check.message
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)

            if (measure_check.is_error and sensor_check.is_error) == False:
                self.updateStatus(deviceID)

    def checkDeviceStatus(self):
        DM.checkUpdate(self, isActuator=False)
        for dev in self.deviceList:
            status = self.checkStatus(dev)
            if status.is_error:
                CompanyName = dev['CompanyName']
                msg = self._message.copy()
                msg['t'] = time.time()
                msg['cn'] = CompanyName
                msg['msgType'] = status.messageType
                msg['msg'] = status.message
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)


def sigterm_handler(signal, frame):
    global run
    run = False
    fd.stop()
    print("FaultDetection stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open('FaultDetectionSettings.json', 'r'))
        ControlPeriod = settings['ControlPeriod']
        fd = FaultDetector(settings)
    except Exception as e:
        print(e)
        print("Error, FaultDetector not initialized")
    else:
        run = True
        while run:
            fd.checkDeviceStatus()
            time.sleep(ControlPeriod)
