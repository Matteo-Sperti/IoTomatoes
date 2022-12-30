import paho.mqtt.client as PahoMQTT
import datetime
import time
import requests
import json
import pandas as pd
import os

class FaultDetector:
	def __init__(self):
		"""Initialize the FaultDetector class"""
		conf = json.load(open('FaultDetectionService_settings.json')) 
		self.clientID = conf['clientID'] #FROM SERVICE CATALOG self.ID
		self.catalogIP = conf['catalogIP']
		self.serviceName = conf['serviceName']

		ServiceInfo = json.loads(requests.get(f'{self.catalogIP}/{self.serviceName}?ID={self.ID}')) # TO CHECK

		self.broker = json.loads(requests.get("self.catalogIP/broker"))
		self.port = ServiceInfo['port']
		self.basicTopic = ServiceInfo['topic']

		r = json.loads(requests.get(f'{self.catalogIP}/getCompanyList'))
		CompanyList = self.updateCompanyList(r['CompanyList'])
		self.deviceList = self.createDeviceList(CompanyList)
		self.thresholds = {
							'temperature' : {'max_value': 4000,'min_value': -100, 'unit': '°C'},
						 	'humidity' : {'max_value': 90, 'min_value': 0, 'unit': '%'},
						  	'light' : {'max_value': 1000, 'min_value': 10**(-5), 'unit': 'lx'}
						  }
		
	def createDeviceList(CompanyList : list):
		"""Create a list of all devices integrating informations about the last time a message was received from a device"""
		deviceList = []
		for comp in CompanyList:
			for dev in comp['deviceList']:
				if(dev['isSensor']):
					deviceList.append(dev.copy().update({'companyName' : comp['companyName'], 'LastUpdate' : None}))
		return deviceList

	def updateDeviceStatus(self, deviceID : str):
		"""Update the status of a device in the deviceList"""
		try:
			for dev in self.deviceList:
				if str(dev['ID']) == deviceID:
					dev['LastUpdate'] = datetime.datetime.now()
					break
		except:
			raise Exception("Device not found")

	def checkDeviceStatus(self,):
		"""Check if a device has not sent a message for more than 5 minutes"""
		currentTime = datetime.datetime.now()
		try:
			for dev in self.deviceList:
				if dev['LastUpdate'] is not None:
					if (currentTime - dev['LastUpdate']).total_seconds() > 300:
						message = "Warning, Device " + str(dev['ID']) + " has not sent a message for more than 5 minutes, possible fault!"
						dict = {'Error': True, 'message' : message, 'deviceID' : dev['ID'], 'companyName' : dev['companyName']}
						return dict
					else:
						dict = {'Error': False}
						return dict
		except:
			raise Exception("Device not found")

	def checkMeasure(self, deviceID: str, measureType: str,  measure : dict):
		"""Check if a measure is within the thresholds"""
		try:
			for dev in self.deviceList:
				if str(dev['ID']) == deviceID:
					if measureType in dev['measureType']:
						if measure > self.thresholds[measureType]['max_value'] or measure < self.thresholds[measureType]['min_value']:
							message = "Warning, Device " + str(dev['ID']) + " has sent a measure out of the thresholds, possible fault!"
							dict = {'Error': True, 'message' : message, 'deviceID' : dev['ID'], 'companyName' : dev['companyName']}
							return dict
						else:
							dict = {'Error': False}
							return dict
		except:
			raise Exception("Device not found")


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
		"""Parse the topic received"""
		topic_list = msg.topic.split('/')
		measureType = topic_list[-1]
		deviceID = topic_list[-2]
		measure = msg.payload['measure']
		dict_msg = self.checkMeasure(deviceID, measureType, measure)
		if dict_msg['Error']:
			self.Publish(dict_msg['message'], f"{self.basicTopic}/{self.serviceName}/alert/measureRange")

	def Publish(self, message, topic):
		"""
			Publishes a message to alert the user of a possible fault
			TOPICS: 
				- IoTomatoes/FaultDetection/alertMeasureRange
				- IoTomatoes/FaultDetection/alertNoMessage
		"""
		self._paho_mqtt.publish(topic, message, 2)

if __name__ == "__main__":
	fd = MQTTFaultDetector()
	while True:
		dict_check = fd.checkDeviceStatus()
		if dict_check['Error']:
			fd.Publish(dict_check['message'], f"{fd.basicTopic}/{fd.serviceName}/alert/noMessage")
		time.sleep(5)
