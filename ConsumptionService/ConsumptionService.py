import paho.mqtt.client as PahoMQTT
import datetime
import time
import requests
import json
import pandas as pd
import os

import sys
sys.path.append('/Users/federicomoscato/IoTomatoes/IoTomatoes')
from Tests.CheckResult import *

class ConsumptionManager:
	def __init__(self):
		"""Initialize the ConsumptionManager class"""

		conf = json.load(open('ConsumptionService_settings.json')) #*TEST
		self.clientID = conf['clientID'] #FROM SERVICE CATALOG self.ID #!FINAL
		self.catalogIP = conf['catalogIP']
		self.serviceName = conf['serviceName']

		#ServiceInfo = json.loads(requests.get(f'{self.catalogIP}/{self.serviceName}?ID={self.ID}')) #!FINAL
		ServiceInfo = {'broker': "mqtt.eclipseprojects.io", 'port': 1883, 'topic': 'IoTomatoes'} #*TEST
		#self.broker = json.loads(requests.get("self.catalogIP/broker"))
		self.broker = ServiceInfo['broker']
		self.port = ServiceInfo['port']
		self.basicTopic = ServiceInfo['topic']

		#r = json.loads(requests.get(f'{self.catalogIP}/getCompanyList')) #!FINAL
		r = json.load(open('../CompanyList.json')) #*TEST
		self.CompanyList = self.updateCompanyList(r['CompanyList'])

	def checkActuator(self, deviceID : int):
		"""Check if an actuator is in the list of the actuators\n
		Parameters:\n
			- deviceID (int) - 'ID of the device to check'\n
		return: CheckResult object with:\n
			- error (bool): ".is_error"\n
			- message (str): ".message"\n
			-  topic (str): ".topic" """

		for comp in self.CompanyList:
			for dev in comp['deviceList']:
				if dev['ID'] == deviceID:
					return CheckResult(is_error = False)
		return CheckResult(is_error=False, message="Error, Actuator not found", topic="ErrorReported")

	def updateCompanyList(self, CompanyList : list):
		"""Update the company list with the actuators status and consumption\n
		Parameters:\n
			- CompanyList (list) - 'List of the companies'\n
		return:\n 
			- CompanyList (list) - 'Updated list of the companies'
		"""
		for comp in CompanyList:
			for dev in comp['deviceList']:
				if dev['isActuator']:
					dev.update({'companyName' : comp['companyName'], 'Datetime' : None, 'status': 'OFF', 'OnTime': 0, 'Consumption_kW' : 0, 'control': False})
		return CompanyList

	def updateConsumption(self):
		"""Calculate the consumption of the actuators for the passed hour and update the database"""
		currentTime = datetime.datetime.now()
		dframe_list = []
		for comp in self.CompanyList:
			actuators = []
			for dev in comp['deviceList']:
				if(dev['isActuator'] and dev['status'] == 'OFF' and dev['control']):
					dev['Datetime']= currentTime #*TEST	  
					#!FINAL: f"{currentTime.date()} {currentTime.hour}:00:00"

					actuators.append(dev.copy())

					dev['Consumption_kW'] = 0
					dev['Datetime'] = None

				elif(dev['isActuator'] and dev['status'] == 'ON' and dev['control']):
					dev['Datetime']= currentTime #*TEST
					#!FINAL: f"{currentTime.date()} {currentTime.hour}:00:00"
					dev['Consumption_kW'] = round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)

					actuators.append(dev.copy())

					dev['OnTime'] = time.time()
					dev['Consumption_kW'] = 0
					dev['Datetime'] = None
			
			df = pd.DataFrame(actuators, columns=['companyName', 'ID', 'deviceName', 'PowerConsumption_kW', 'Datetime', 'Consumption_kW'])
			dframe_list.append(df)

		db = pd.read_csv('Consumption.csv') 
		dframe_list.insert(0, db)
		df = pd.concat(dframe_list)
		df = df.reset_index(drop=True)	
		print(df)			  #? TO CHECK with mongoDB		
		df.to_csv('Consumption.csv', index=False) #!!!!! PUT REQUEST TO DATABASE TODO

	def upgradeStatus (self, actuatorID: str, command: str):
		"""Update the status of the actuator, if it is turned OFF calculates its consumption\n
		Parameters:\n
			- companyName (str) - 'Name of the company'\n
			- actuatorID (str) - 'ID of the actuator'\n
			- command (str) - 'Command sent to the actuator'\n
		"""

		for comp in self.CompanyList :
				for dev in comp['deviceList']:
					if dev['ID'] == actuatorID:
						if command == 'ON':
							dev['status'] = command
							dev['OnTime'] = time.time()
							dev['control'] = True
							return CheckResult(is_error=False)
						elif command == 'OFF':
							dev['status'] = command
							#Calculate the consumption of a actuator by its mean power consumption and the time it was on 
							dev['Consumption_kW'] += round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)
							dev['OnTime'] = 0
							return CheckResult(is_error=False)
						else:
							return CheckResult(is_error=True, message="Error, command not recognized", topic="ErrorReported")
		return CheckResult(is_error=True, message="Error, Actuator not found", topic="ErrorReported")

class MQTTConsumptionManager(ConsumptionManager):
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
		for comp in self.CompanyList:
			for dev in comp['deviceList']:
				if dev['isActuator']:
					topics.append(f"{self.basicTopic}/{comp['companyName']}/{dev['field']}/{dev['ID']}/command")
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
		"""Parse the message received and control the topic\n
			Subscribed topics format:\n
				- IoTomatoes/CompanyName/Field/ActuatorID/command
		"""
		command = json.loads(msg.payload).get('command')
		topic_list = msg.topic.split('/')
		ActuatorID = int(topic_list[-2])
		companyName = topic_list[-4]
		check_actuator = self.checkActuator(ActuatorID)

		if check_actuator.is_error:
			self.Publish(f"{companyName}/{check_actuator.topic}", check_actuator.message)
		else:
			self.upgradeStatus(ActuatorID, command)

	def Publish(self, topic, message):
		"""
			Publishes a message to alert the user of a possible fault\n
			TOPICS:\n 
				- IoTomatoes/ConsumptionManagement/CompanyName/ErrorReported
		"""
		topic_sent = f"{self.basicTopic}/{self.serviceName}/{topic}"
		payload = json.dumps({'message': message})
		self._paho_mqtt.publish(topic_sent, payload, 2)


if __name__ == "__main__":
	cm = MQTTConsumptionManager()
	while True:
		#if datetime.datetime.now().second >= 59: #Update the consumption every minute #!FINAL
		time.sleep(30) #!FINAL: 60
		cm.updateConsumption()
