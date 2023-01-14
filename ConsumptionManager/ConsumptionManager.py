import paho.mqtt.client as PahoMQTT
import requests
import datetime
import time
import json
import pandas as pd

import sys
sys.path.append('../SupportClasses/')
from CheckResult import *
from GenericEndpoint import GenericEndpoint
from DeviceManager import *


class ConsumptionManager (GenericEndpoint):
	def __init__(self, settings):
		"""Initialize the ConsumptionManager class"""

		super().__init__(settings, isService=True)

		self.deviceList = getDevicesList(self.ResourceCatalog_url, self._SystemToken, isActuator=True)

	def updateConsumption(self):
		"""Calculate the consumption of the actuators for the passed hour and update the database"""
		currentTime = datetime.datetime.now()
		dframe_list = []
		for dev in self.deviceList:
			actuators = []
			if(dev['status'] == 'OFF' and dev['control']):
				dev['Datetime']= currentTime #*TEST	  
				#!FINAL: f"{currentTime.date()} {currentTime.hour}:00:00"

				actuators.append(dev.copy())

				dev['Consumption_kW'] = 0
				dev['Datetime'] = None

			elif(dev['status'] == 'ON' and dev['control']):
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

	def updateStatus (self, actuatorID: int, command: str):
		"""Update the status of the actuator, if it is turned OFF calculates its consumption\n
		Parameters:\n
			- companyName (str) - 'Name of the company'\n
			- actuatorID (str) - 'ID of the actuator'\n
			- command (str) - 'Command sent to the actuator'\n
		"""
		for dev in self.deviceList:
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
					return CheckResult(is_error=True, message="Error, command not recognized", topic=self._publishedTopics[0])
		return CheckResult(is_error=True, message="Error, Actuator not found.", topic=self._publishedTopics[0])

	def notify (self, topic, payload):
		"""Parse the message received and control the topic\n
			Subscribed topics format:\n
				- IoTomatoes/CompanyName/Field/ActuatorID/actuatorType
		"""
		topic_list = topic.split('/')
		ActuatorID = int(topic_list[-2])
		companyName = topic_list[-4]
		try:
			command = payload['command']
		except:
			payload = json.dumps({'message': "Error, command not found", 'companyName': companyName})
			self.myPublish(f"{self._baseTopic}/{self._publishedTopics[0]}", payload)
		else:
			check_actuator = inList(ActuatorID, self.deviceList)
			if check_actuator.is_error:
				payload = {'message': check_actuator.message}
				self.myPublish(f"{self._baseTopic}/{companyName}/{self._publishedTopics[0]}", payload)
			else:
				self.updateStatus(ActuatorID, command)

if __name__ == "__main__":
	try:
		settings = json.load(open('ConsumptionServiceSettings.json', 'r'))
		cm = ConsumptionManager(settings)
	except Exception as e:
		print(e)
		print("Error, ConsumptionManager not initialized")
	else:
		while True:
			checkUpdate(cm, True)
			if datetime.datetime.now().second >= 59: #Update the consumption every hour
				cm.updateConsumption()
			time.sleep(60)