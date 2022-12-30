import paho.mqtt.client as PahoMQTT
import time
import json
import random

class FakeActuatorCommands:
	def __init__(self, clientID,broker):
		self.clientID = clientID #UNIQUE ID!
		self.topic = ""
		# create an instance of paho.mqtt.client
		self._paho_mqtt = PahoMQTT.Client(self.clientID,True) 
		# register the callback
		self._paho_mqtt.on_connect = self.myOnConnect
		#self.messageBroker = 'iot.eclipse.org'
		self.messageBroker = broker

	def start (self):
		#manage connection to broker
		self._paho_mqtt.connect(self.messageBroker, 1883)
		self._paho_mqtt.loop_start()

	def stop (self):
		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()

	def myPublish(self,message):
		# publish a message with a certain topic
		self._paho_mqtt.publish(self.topic, message, 2)

	def myOnConnect (self, paho_mqtt, userdata, flags, rc):
		print ("Connected to %s with result code: %d" % (self.messageBroker, rc))




if __name__ == "__main__":
	test = FakeActuatorCommands("fakeActuatorCommands",'mqtt.eclipseprojects.io')
	test.start()
	
	iter = 0
	dict = json.load(open('CompanyList.json'))
	while(True):
		for company in dict['CompanyList']:
			for device in company['deviceList']:
				if device['isActuator']:
					topic = f"IoTomatoes/{company['companyName']}/{device['ID']}/command"
					print(topic)
					test.topic = topic
					if iter == 0:
						device.update({'status': None})
					else:
						if(device['status'] == 'OFF' or device['status'] == None):
							device['status'] = 'ON'
							test.myPublish(json.dumps({"status": device['status']}))
						elif(device['status'] == 'ON'):
							device['status'] = 'OFF'
							test.myPublish(json.dumps({"status": device['status']}))
						else:
							print("ERROR")
						print("Payload sent: ",device['status'], "\n")
		print("\n")
		iter+=1
		time.sleep(round(random.uniform(1,5)))

	test.stop()
