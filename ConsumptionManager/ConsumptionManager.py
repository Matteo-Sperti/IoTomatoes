import datetime
import time
import json

from iotomatoes_supportpackage.GenericEndpoint import GenericService
import iotomatoes_supportpackage.DeviceManager as DM

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
		self.deviceList = DM.createDeviceList(companyList, isActuator=True)

	def updateConsumption(self):
		"""Calculate the consumption of the actuators for the passed hour and update the database"""

		for dev in self.deviceList:
			if(dev['status'] == 'OFF' and dev['control']):
				dev_consumption = {
					'companyName': dev['companyName'],	
					'bn': dev['ID'],
					'field': dev['field'],
					'consumption': {
						'consumption_value': dev['Consumption_kWh'],
						'unit': 'kWh',
						'power': dev['PowerConsumption_kW'],
						'timestamp': time.time()
					}
				}
				dev['Consumption_kWh'] = 0
				self.myPublish(f"{dev['companyName']}/consumption", dev_consumption)

			elif(dev['status'] == 'ON' and dev['control']):
				dev['Consumption_kWh'] = round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)
				dev_consumption = {
					'companyName': dev['companyName'],	
					'bn': dev['ID'],
					'field': dev['field'],
					'consumption': {
						'consumption_value': dev['Consumption_kWh'],
						'unit': 'kWh',
						'power': dev['PowerConsumption_kW'],
						'timestamp': time.time()
					}
				}
				dev['OnTime'] = time.time()
				dev['Consumption_kWh'] = 0
				self.myPublish(f"{dev['companyName']}/consumption", dev_consumption)

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
					return DM.CheckResult(is_error=False)
				elif command == 0:
					dev['status'] = 'OFF'
					#Calculate the consumption of a actuator by its mean power consumption and the time it was on 
					dev['Consumption_kWh'] += round((time.time() - dev['OnTime'])*dev['PowerConsumption_kW']/3600,2)
					dev['OnTime'] = 0
					return DM.CheckResult(is_error=False)
				else:
					return DM.CheckResult(is_error=True, messageType="Error", message="Command not recognized")
		return DM.CheckResult(is_error=True, messageType="Error", message="Actuator not found.")

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
			DM.checkUpdate(self, True)
			check_actuator = DM.inList(ActuatorID, self.deviceList)
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
		settings = json.load(open('ConsumptionManagerSettings.json', 'r'))
		cm = ConsumptionManager(settings)
	except Exception as e:
		print(e)
		print("Error, ConsumptionManager not initialized")
	else:
		try:
			while True:
				#!To change for testing
				if datetime.datetime.now().second >= 59: #Update the consumption every hour 
					cm.updateConsumption()
				time.sleep(60)
		except KeyboardInterrupt:
			cm.stop()
			print("ConsumptionManager stopped")