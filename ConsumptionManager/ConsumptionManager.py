import datetime
import time
import json
import pandas as pd

import sys
sys.path.append('../SupportClasses/')
from GenericEndpoint import GenericService
from DeviceManager import *


class ConsumptionManager (GenericService):
	def __init__(self, settings):
		"""Initialize the ConsumptionManager class"""

		super().__init__(settings)
		self._message = {
					'bn' : self._EndpointInfo['serviceName'],
					'cn': "",
					'msgType': '',
					'msg': "", 
					't' : ""
					}
		companyList = self.getCompaniesList()
		self.deviceList = createDeviceList(companyList, isActuator=True)

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

				dev['Consumption_kWh'] = 0
				dev['Datetime'] = None

			elif(dev['status'] == 'ON' and dev['control']):
				dev['Datetime']= currentTime #*TEST
				#!FINAL: f"{currentTime.date()} {currentTime.hour}:00:00"
				dev['Consumption_kWh'] = round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)

				actuators.append(dev.copy())

				dev['OnTime'] = time.time()
				dev['Consumption_kWh'] = 0
				dev['Datetime'] = None
			
			df = pd.DataFrame(actuators, columns=['companyName', 'ID', 'deviceName', 'PowerConsumption_kW', 'Datetime', 'Consumption_kWh'])
			dframe_list.append(df)

		db = pd.read_csv('Consumption.csv') 
		dframe_list.insert(0, db)
		df = pd.concat(dframe_list)
		df = df.reset_index(drop=True)	
		print(df)			  #? TO CHECK with mongoDB		
		df.to_csv('Consumption.csv', index=False) #!!!!! PUT REQUEST TO DATABASE TODO

	def updateStatus (self, actuatorID: int, command: str):
		"""Update the status of the actuator, if it is turned OFF calculates its consumption\n
		Arguments:\n
		`actuatorID (str)` : ID of the actuator\n
		`command (str)` : Command sent to the actuator\n
		"""
		for dev in self.deviceList:
			if dev['ID'] == actuatorID:
				if command == 1:
					dev['status'] = 'ON'
					dev['OnTime'] = time.time()
					dev['control'] = True
					return CheckResult(is_error=False)
				elif command == 0:
					dev['status'] = 'OFF'
					#Calculate the consumption of a actuator by its mean power consumption and the time it was on 
					dev['Consumption_kWh'] += round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)
					dev['OnTime'] = 0
					return CheckResult(is_error=False)
				else:
					return CheckResult(is_error=True, messageType="Error", message="Command not recognized")
		return CheckResult(is_error=True, messageType="Error", message="Actuator not found.")

	def notify (self, topic, payload):
		"""Parse the message received and control the topic\n
			Subscribed topics format:\n
				- IoTomatoes/CompanyName/Field/ActuatorID/actuatorType
		"""
		topic_list = topic.split('/')
		ActuatorID = int(topic_list[-2])
		companyName = topic_list[-4]
		try:
			command = payload['e'][-1]['v']
		except:
			msg = self._message.copy()
			msg['cn'] = companyName
			msg['msg'] = "Error in the payload"
			msg['msgType'] = "Error"
			msg['t'] = time.time()
			self.myPublish(f"{self._publishedTopics[0]}", msg)
		else:
			checkUpdate(self, True)
			check_actuator = inList(ActuatorID, self.deviceList)
			if check_actuator.is_error:
				msg = self._message.copy()
				msg['cn'] = companyName
				msg['msg'] = check_actuator.message
				msg['msgType'] = check_actuator.messageType
				msg['t'] = time.time()
				self.myPublish(f"{companyName}/{self._publishedTopics[0]}", msg)
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
		try:
			while True:
				if datetime.datetime.now().second >= 59: #Update the consumption every hour
					cm.updateConsumption()
				time.sleep(60)
		except KeyboardInterrupt:
			cm.stop()
			print("ConsumptionManager stopped")

