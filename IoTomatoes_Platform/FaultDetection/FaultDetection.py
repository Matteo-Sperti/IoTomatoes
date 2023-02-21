import datetime
import time
import json
import signal
import requests

from iotomatoes_supportpackage import BaseService, CheckResult


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
        self.deviceList = []
        self.updateDeviceList()

    @property
    def deviceList(self):
        return self._deviceList

    @deviceList.setter
    def deviceList(self, new_deviceList: list):
        self._deviceList = new_deviceList

    def updateDeviceList(self):
        """Get the list of actuators"""

        resourceManager_url = self.getOtherServiceURL(
            self.resourceManagerToCall)
        if resourceManager_url == None or resourceManager_url == "":
            print("ERROR: resource manager service not found!")
            return

        try:
            status_data = requests.get(
                f'{resourceManager_url}/checkSensorUpdates')
            status = status_data.json()['status']
            if status == True:
                devices_data = requests.get(
                    f'{resourceManager_url}/getSensors')
                new_deviceList = devices_data.json()
                self.deviceList = new_deviceList
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
        - `error (bool)`: ".is_error"
        - `message (str)`: ".message"
        """

        currentTime = datetime.datetime.now()
        if device['lastMeasure'] is not None:
            elapsedTime = (currentTime - device['lastMeasure']).total_seconds()
            if elapsedTime > 300:
                message = f"Device {device['ID']} has not sent a message for more than 5 minutes, possible fault!"
                return CheckResult(is_error=True, messageType="Warning", message=message,
                                   device_id=device['ID'])
            else:
                return CheckResult(is_error=False)
        return CheckResult(is_error=False)

    def checkMeasure(self, deviceID: int, measureType: str,  measure, unit: str):
        """Check if a measure is out of the thresholds.

        Arguments:\n
        - `deviceID (int)`: ID of the device
        - `measureType (str)`: Type of the measure to check
        - `measure (float)`: Value of the measure to check

        Return: `CheckResult` object with:
        - `error (bool)`: ".is_error"
        - `message (str)`: ".message"
        """

        if unit != self.thresholds[measureType]['unit']:
            return CheckResult(is_error=True, messageType="Error",
                               message=f"Unit of measure '{unit}' of device {deviceID} not recognized.")

        if self.deviceList == []:
            return CheckResult(is_error=False)
        
        device = None
        for dev in self.deviceList:
            if dev['ID'] == deviceID:
                device = dev
                break
        if not device:
            return CheckResult(is_error=True, messageType="Error", message="Device not found")
        
        if measureType == 'position':
            try:
                position_data = requests.get(
                    f"{self.ResourceCatalog_url}/{device['CompanyName']}/location")
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
                return CheckResult(is_error=True, messageType="Error",
                                   message=f"Position of company {device['CompanyName']} not found.")
            if (measure['latitude'] > max_latitude or measure['latitude'] < min_latitude) or \
                    (measure['longitude'] > max_longitude or measure['longitude'] < min_longitude):
                message = (f"Device {deviceID} is out of the defined range, possible fault!\n"
                           f"Value = {measure['latitude']}, {measure['longitude']} {unit}")
                return CheckResult(is_error=True, messageType="Warning", message=message,
                                   device_id=deviceID)
        else:
            if measureType not in device['measureType']:
                return CheckResult(is_error=True, messageType="Error",
                                   message=f"Measure type of device {deviceID} not recognized.")

            min_value = self.thresholds[measureType]['min_value']
            max_value = self.thresholds[measureType]['max_value']

            if min_value is None or max_value is None:
                return CheckResult(is_error=True, messageType="Error", message="Thresholds not configured")

            if measure > max_value or measure < min_value:
                message = (f"Device {deviceID} has sent a measure out of the thresholds, possible fault!\n"
                           f"Value = {measure} {unit}")
                return CheckResult(is_error=True, messageType="Warning", message=message,
                                   device_id=deviceID)
        return CheckResult(is_error=False)

    def notify(self, topic, payload):
        """Parse the topic received, check the device status and the measure 
        and publish the alert messages if needed.

        Subscribed TOPICS format:
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
            self.updateDeviceList()
            found = False
            for dev in self.deviceList:
                if dev['ID'] == deviceID:
                    found = True

            measure_check = self.checkMeasure(
                deviceID, measureType, measure, unit)
            if not found and self.deviceList != []:
                msg = self._message.copy()
                msg['t'] = time.time()
                msg['cn'] = CompanyName
                msg['msgType'] = "Error"
                msg['msg'] = f"Device {deviceID} not found"
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
            elif measure_check.is_error:
                msg = self._message.copy()
                msg['t'] = time.time()
                msg['cn'] = CompanyName
                msg['msgType'] = measure_check.messageType
                msg['msg'] = measure_check.message
                self._MQTTClient.myPublish(
                    f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)

            if not measure_check.is_error and found:
                self.updateStatus(deviceID)

    def checkDeviceStatus(self):
        """Check the status of all the devices in the deviceList and publish the alert messages if needed.
        """
        self.updateDeviceList()
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
    """Handler for SIGTERM signal.
    Stop the FaultDetection."""

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
