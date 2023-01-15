import datetime
import time
import json

import sys
sys.path.append('../SupportClasses/')
from MyExceptions import CheckResult
from GenericEndpoint import GenericService
from DeviceManager import *

class FaultDetector(GenericService):
	def __init__(self, settings):
		"""Initialize the FaultDetector class"""

		self.thresholds = settings['thresholds']

		super().__init__(settings)

		companyList = self.getCompaniesList()
		self.deviceList = createDeviceList(companyList, isActuator=False)

	def updateStatus(self, deviceID : int):
		"""Update the status of a device in the deviceList\n
		Arguments:\n
		`deviceID (int)`: ID of the device to update
		"""
		
		for dev in self.deviceList:
			if dev['ID'] == deviceID:
				dev['lastUpdate'] = datetime.datetime.now()
				break

	def checkStatus(self, device : dict):
		"""Check if a device has not sent a message for more than 5 minutes\n
		Arguments:\n
		`device (dict)`: Device to check\n
		Return:\n
		`CheckResult` object with:\n
		`error (bool)`: ".is_error"\n
		`message (str)`: ".message"\n
		` topic (str)`: ".topic" 
		"""

		currentTime = datetime.datetime.now()
		if device['lastUpdate'] is not None:
			elapsedTime = (currentTime - device['lastUpdate']).total_seconds()
			if elapsedTime > 300:
				message = f"Warning, Device {device['ID']} has not sent a message for more than 5 minutes, possible fault!"
				return CheckResult(is_error=True, message=message, device_id=device['ID'], topic=self._publishedTopics[2])
			else:
				return CheckResult(is_error=False)
		return CheckResult(is_error=False)

	def checkMeasure(self, deviceID: int, measureType: str,  measure : float):
		"""Check if a measure is out of the thresholds\n
		Arguments:\n
		`deviceID (int)`: ID of the device\n
		`measureType (str)`: Type of the measure to check\n
		`measure (float)`: Value of the measure to check\n
		Return:\n
		`CheckResult` object with:\n
		`error (bool)`: ".is_error"\n
		`message (str)`: ".message"\n
		`topic (str)`: ".topic" """

		device = None

		for dev in self.deviceList:
			if dev['ID'] == deviceID:
				device = dev
				break
		if not device:
			return CheckResult(is_error=True, message="Error, Device not found", topic=self._publishedTopics[0]) 
		if measureType not in device['measureType']:
			return CheckResult(is_error=True, message=f"Error, Measure type of device {deviceID} not recognized.", topic=self._publishedTopics[0]) 

		min_value = self.thresholds[measureType]['min_value']
		max_value = self.thresholds[measureType]['max_value']

		if min_value is None or max_value is None:
			return CheckResult(is_error=True, message="Error, Thresholds not configured", topic=self._publishedTopics[0])

		if measure > max_value or measure < min_value:
			message = f"Warning, Device {deviceID} has sent a measure out of the thresholds, possible fault!"
			return CheckResult(is_error=True, message=message, device_id=deviceID, topic=self._publishedTopics[1])
		return CheckResult(is_error=False)

	def notify(self, topic, payload):
		"""Parse the topic received, check the device status and the measure and publish the alert messages if needed.\n
			Subscribed TOPICS format:\n
				- IoTomatoes/CompanyName/Field/DeviceID/MeasureType
		"""
		topic_list = topic.split('/')
		measureType = topic_list[-1]
		deviceID = int(topic_list[-2])
		companyName = topic_list[-4]
		try:
			measure = payload['e'][-1]['v']
		except:
			msg = {'bn' : self._EndpointInfo['serviceName'],
					'cn': companyName,
					'msg': "Error, measure not found", 
					't' : time.time()}
			self.myPublish(f"{companyName}/{self._publishedTopics[0]}", msg)
		else:
			sensor_check = inList(deviceID, self.deviceList)
			measure_check = self.checkMeasure(deviceID, measureType, measure)
			if sensor_check.is_error:
				msg = {'bn' : self._EndpointInfo['serviceName'],
						'cn': companyName,
						'msg': sensor_check.message, 
						't' : time.time()}
				self.myPublish(f"{companyName}/{sensor_check.topic}", msg)
			if measure_check.is_error:
				msg = {'bn' : self._EndpointInfo['serviceName'],
						'cn': companyName,
						'msg': measure_check.message, 
						't' : time.time()}
				self.myPublish(f"{companyName}/{measure_check.topic}", msg)
			
			if (measure_check.is_error and sensor_check.is_error) == False:
				self.updateStatus(deviceID)

if __name__ == "__main__":
	try:
		settings = json.load(open('FaultDetectionServiceSettings.json', 'r'))
		fd = FaultDetector(settings)
	except Exception as e:
		print(e)
		print("Error, FaultDetector not initialized")
	else:
		try:
			while True:
				time.sleep(60)
				checkUpdate(fd, isActuator=False)
				for dev in fd.deviceList:
					status = fd.checkStatus(dev)
					if status.is_error:
						companyName = dev['companyName']
						msg = {'bn': fd._EndpointInfo['serviceName'],
								'cn': companyName,
								'msg': status.message, 
								't' : time.time()}
						fd.myPublish(f"{companyName}/{status.topic}", msg)
		except KeyboardInterrupt:
			fd.stop()
			print("FaultDetection stopped")

		