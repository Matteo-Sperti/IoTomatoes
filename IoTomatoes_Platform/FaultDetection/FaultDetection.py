import datetime
import time
import json
import signal

from iotomatoes_supportpackage.BaseService import BaseService
import iotomatoes_supportpackage.DeviceManager as DM

class FaultDetector(BaseService):
	def __init__(self, settings):
		"""Initialize the FaultDetector class"""

		self.thresholds = settings['thresholds']

		super().__init__(settings)
		self._message = {
					'bn' : self.EndpointInfo['serviceName'],
					'cn': '',
					'msgType': '',
					'msg': '', 
					't' : ''
					}
		companyList = self.getCompaniesList()
		self.deviceList = DM.createDeviceList(companyList, isActuator=False)

	def updateStatus(self, deviceID : int):
		"""Update the status of a device in the deviceList
		
		Arguments:
		- `deviceID (int)`: ID of the device to update
		"""
		
		for dev in self.deviceList:
			if dev['ID'] == deviceID:
				dev['lastMeasure'] = datetime.datetime.now()
				break

	def checkStatus(self, device : dict):
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

	def checkMeasure(self, deviceID: int, measureType: str,  measure : float, unit : str):
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
				- IoTomatoes/CompanyName/Field/DeviceID/MeasureType
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
			self._MQTTClient.myPublish(f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
		else:
			DM.checkUpdate(self, False)
			sensor_check = DM.inList(deviceID, self.deviceList)
			measure_check = self.checkMeasure(deviceID, measureType, measure, unit)
			if sensor_check.is_error:
				msg = self._message.copy()
				msg['t'] = time.time()
				msg['cn'] = CompanyName
				msg['msgType'] = sensor_check.messageType
				msg['msg'] = sensor_check.message
				self._MQTTClient.myPublish(f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
			if measure_check.is_error:
				msg = self._message.copy()
				msg['t'] = time.time()
				msg['cn'] = CompanyName
				msg['msgType'] = measure_check.messageType
				msg['msg'] = measure_check.message
				self._MQTTClient.myPublish(f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)
			
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
				self._MQTTClient.myPublish(f"{CompanyName}/{self._MQTTClient.publishedTopics[0]}", msg)

def sigterm_handler(signal, frame):
    fd.stop()
    print("FaultDetection stopped")

signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
	try:
		settings = json.load(open('FaultDetectionSettings.json', 'r'))
		fd = FaultDetector(settings)
	except Exception as e:
		print(e)
		print("Error, FaultDetector not initialized")
	else:
		while True:
			fd.checkDeviceStatus()
			time.sleep(60)

		