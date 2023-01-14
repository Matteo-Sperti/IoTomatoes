import paho.mqtt.client as PahoMQTT
import datetime
import time
import requests
import json
import pandas as pd

import sys
sys.path.append('../')
from Tests.CheckResult import *
from SupportClasses.GenericEndpoint import GenericEndpoint

class FaultDetector:
	def __init__(self):
		"""Initialize the FaultDetector class"""
		conf = json.load(open('FaultDetectionService_settings.json')) 
		self.clientID = conf['clientID'] #!FINAL: FROM SERVICE CATALOG self.ID
		self.catalogIP = conf['catalogIP']
		self.serviceName = conf['serviceName']
		self.thresholds = conf['thresholds']

		#ServiceInfo = json.loads(requests.get(f'{self.catalogIP}/{self.serviceName}?ID={self.ID}')) #!FINAL
		ServiceInfo = {'broker': "mqtt.eclipseprojects.io", 'port': 1883, 'topic': 'IoTomatoes'} #*TEST
		#self.broker = json.loads(requests.get("self.catalogIP/broker")) #!FINAL
		self.broker = ServiceInfo['broker'] #*TEST
		self.port = ServiceInfo['port']
		self.basicTopic = ServiceInfo['topic']

		#r = json.loads(requests.get(f'{self.catalogIP}/getCompanyList')) #!FINAL
		CompanyList = json.load(open("../CompanyList.json")) #*TEST
		self.deviceList = self.createDeviceList(CompanyList['CompanyList'])
	def createDeviceList(self, CompanyList):
		"""Create a list of all devices integrating informations about the last time a message was received from a device\n
		Parameters:\n
			 - CompanyList (list of dict) - 'List of all companies and their devices'\n
		return: \n
			- deviceList (list of dict) - 'List of all devices updated'"""
		deviceList = []
		for comp in CompanyList:
			for dev in comp['deviceList']:
				if dev['isSensor']:
					deviceList.append({**dev, **{'companyName': comp['companyName'], 'LastUpdate': None}})
		return deviceList

	def updateDeviceStatus(self, deviceID : int):
		"""Update the status of a device in the deviceList\n
		Parameters:\n
			- deviceID (int) - 'ID of the device to update'"""
		
		for dev in self.deviceList:
			if dev['ID'] == deviceID:
				dev['LastUpdate'] = datetime.datetime.now()
				break

	def checkDeviceStatus(self, device : dict):
		"""Check if a device has not sent a message for more than 5 minutes\n
		Parameters:\n
		 	- device (dict) - 'Device to check'\n
		return: CheckResult object with:\n
			- error (bool): ".is_error"\n
			- message (str): ".message"\n
			-  topic (str): ".topic" """

		currentTime = datetime.datetime.now()
		if device['LastUpdate'] is not None:
			elapsedTime = (currentTime - device['LastUpdate']).total_seconds()
			if elapsedTime > 2:
				message = f"Warning, Device {device['ID']} has not sent a message for more than 5 minutes, possible fault!"
				return CheckResult(is_error=True, message=message, device_id=device['ID'], topic="alertNoMessage")
			else:
				return CheckResult(is_error=False)
		return CheckResult(is_error=False)

	def checkMeasure(self, companyName: str, deviceID: int, measureType: str,  measure : float):
		"""Check if a measure is out of the thresholds\n
		Parameters:\n
			- companyName (str) - 'Name of the company of the device'\n
			- deviceID (int) - 'ID of the device'\n
			- measureType (str) - 'Type of the measure to check'\n
			- measure (float) - 'Value of the measure to check'\n
		return: CheckResult object with:\n
			- error (bool): ".is_error"\n
			- message (str): ".message"\n
			-  topic (str): ".topic" """

		device = None

		for dev in self.deviceList:
			if dev['ID'] == deviceID:
				device = dev
				break
		if not device:
			return CheckResult(is_error=True, message="Error, Device not found", topic="ErrorReported") 
		if measureType not in device['measureType']:
			return CheckResult(is_error=True, message=f"Error, Measure type of device {deviceID} not recognized.", topic="ErrorReported") 

		min_value = self.thresholds[measureType]['min_value']
		max_value = self.thresholds[measureType]['max_value']

		if min_value is None or max_value is None:
			return CheckResult(is_error=True, message="Error, Thresholds not configured", topic="ErrorReported")

		if measure > max_value or measure < min_value:
			message = f"Warning, Device {deviceID} has sent a measure out of the thresholds, possible fault!"
			return CheckResult(is_error=True, message=message, device_id=deviceID, topic="alertMeasureRange")
		return CheckResult(is_error=False)


class MQTTFaultDetector(FaultDetector):
	def __init__(self):
		super().__init__()
		self.topics = self.createTopics()
		
		self._paho_mqtt = PahoMQTT.Client(self.clientID, True)
		self.start()
		self._paho_mqtt.on_connect = self.OnConnect
		self._paho_mqtt.on_message = self.MessageReceived

	def createTopics(self):
		"""Create the topics for each actuator of each company"""
		topics = []
		for dev in self.deviceList:
			for measure in dev['measureType']:
				topics.append(f"{self.basicTopic}/{dev['companyName']}/{dev['ID']}/{measure}")
		return topics

	def start (self):
		"""Connect to the broker and subscribe to the topics"""
		self._paho_mqtt.connect(self.broker, self.port)
		self._paho_mqtt.loop_start()
		# subscribe for a topic
		for i in self.topics:
			self._paho_mqtt.subscribe(i, 2)

	def stop (self):
		"""Disconnect from the broker and unsubscribe from the topics"""
		for i in self.topics:
			self._paho_mqtt.unsubscribe(i)
		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()

	def OnConnect (self, paho_mqtt, userdata, flags, rc):
		print ("Connected to %s with result code: %d" % (self.broker, rc))

	def MessageReceived (self, paho_mqtt , userdata, msg):
		"""Parse the topic received, check the device status and the measure and publish the alert messages if needed.\n
			Subscribed TOPICS format:\n
				- IoTomatoes/CompanyName/Field/DeviceID/MeasureType
		"""
		topic_list = msg.topic.split('/')
		measureType = topic_list[-1]
		deviceID = int(topic_list[-2])
		companyName = topic_list[-4]
		measure = json.loads(msg.payload).get('measure')

		measure_check = self.checkMeasure(companyName, deviceID, measureType, measure)
		if measure_check.is_error:
			self.Publish(measure_check.message, f"{companyName}/{measure_check.topic}")
		else:
			self.updateDeviceStatus(deviceID)

	def Publish(self, message, topic):
		"""
			Publishes a message to alert the user of a possible fault\n
			TOPICS:\n 
				- IoTomatoes/FaultDetection/CompanyName/alertMeasureRange
				- IoTomatoes/FaultDetection/CompanyName/alertNoMessage
				- IoTomatoes/FaultDetection/CompanyName/ErrorReported
		"""
		topic_sent = f"{self.basicTopic}/{self.serviceName}/{topic}"
		payload =json.dumps({'message': message})
		self._paho_mqtt.publish(topic_sent, payload, 2)

if __name__ == "__main__":
	fd = MQTTFaultDetector()
	while True:
		time.sleep(5) #!FINAL: 300

		for dev in fd.deviceList:
			status = fd.checkDeviceStatus(dev)
			if status.is_error:
				payload_message = status.message
				companyName = dev['companyName']
				fd.Publish(payload_message, f"{companyName}/{status.topic}")

		