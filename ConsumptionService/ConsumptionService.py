import paho.mqtt.client as PahoMQTT
import datetime
import time
import requests
import json
import pandas as pd
import os

class ConsumptionManager:
	def __init__(self):
		"""Initialize the ConsumptionManager class"""

		conf = json.load(open('ConsumptionService_settings.json')) 
		self.clientID = conf['clientID'] #FROM SERVICE CATALOG self.ID
		self.catalogIP = conf['catalogIP']
		self.serviceName = conf['serviceName']

		ServiceInfo = json.loads(requests.get(f'{self.catalogIP}/{self.serviceName}?ID={self.ID}')) # TO CHECK

		self.broker = json.loads(requests.get("self.catalogIP/broker"))
		self.port = ServiceInfo['port']
		self.basicTopics = ServiceInfo['topic']

		r = json.loads(requests.get(f'{self.catalogIP}/getCompanyList'))
		self.CompanyList = self.updateCompanyList(r['CompanyList'])

	def updateCompanyList(CompanyList : list):
		"""Update the company list with the actuators status and consumption"""
		for comp in CompanyList:
			for dev in comp['deviceList']:
				if dev['isActuator']:
					dev.update({'companyName' : comp['companyName'], 'Datetime' : None, 'status': 'OFF', 'OnTime': 0, 'Consumption' : 0})
		return CompanyList

	def updateConsumption(self):
		"""Calculate the consumption of the actuators for the passed hour and update the database"""
		currentTime = datetime.datetime.now()
		dframe_list = []
		for comp in self.CompanyList:
			actuators = []
			for dev in comp['deviceList']:
				if(dev['isActuator'] and dev['status'] == 'OFF'):
					dev['Datetime']= f"{currentTime.date()} {currentTime.hour}:00:00"

					actuators.append(dev.copy())

					dev['Consumption'] = 0
					dev['Datetime'] = None

				elif(dev['isActuator'] and dev['status'] == 'ON'):
					dev['Datetime']= f"{currentTime.date()} {currentTime.hour}:00:00"
					dev['Consumption'] = round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)

					actuators.append(dev.copy())

					dev['OnTime'] = time.time()
					dev['Consumption'] = 0
					dev['Datetime'] = None

			df = pd.DataFrame(actuators, columns=['companyName', 'ID', 'deviceName', 'PowerConsumption_kW', 'Datetime', 'Consumption'])
			dframe_list.append(df)
		df = pd.concat(dframe_list)
		df.to_csv('Consumption.csv', index=False) #!!!!! PUT REQUEST TO DATABASE TODO

	def upgradeStatus (self, companyName: str, actuatorID: str, command: str):
		"""Update the status of the actuator, if it is turned OFF calculates its consumption"""
		try:
			for comp in self.CompanyList:
				if comp['comapnyName'] == companyName:
					for dev in comp:
						if dev['deviceName'] == actuatorID:
							if command == 'ON':
								dev['status'] = command
								dev['OnTime'] = time.time()
							elif command == 'OFF':
								dev['status'] = command
								#Calculate the consumption of a actuator by its mean power consumption and the time it was on 
								dev['Consumption'] += round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)
								dev['OnTime'] = 0
							else:
								raise Exception("Wrong message")
						return
			raise Exception("Actuator or Company not found")
		except Exception as e:
			raise e

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
					topics.append(f"{self.basicTopics}/{comp['companyName']}/{dev['ID']}")
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
		"""Parse the message received and control the topic"""
		try:
			command = list[msg.payload.values()][0]
			head, deviceID = os.path.split(msg.topic)
			topic, companyName = os.path.split(head)
			if topic not in self.basicTopics:
				raise ValueError("Topic not valid")
			else:
				self.upgradeStatus(companyName, deviceID, command)
		except ValueError as e:
			print(e)


if __name__ == "__main__":
	cm = MQTTConsumptionManager()
	while True:
		if datetime.now().minute >= 59: #Update the consumption every hour
			cm.updateConsumption()
		time.sleep(60)
