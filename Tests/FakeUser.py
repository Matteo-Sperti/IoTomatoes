import paho.mqtt.client as PahoMQTT
import json

class FakeUser():
	def __init__(self):
		self.clientID = "FakeUser"
		self.broker = "mqtt.eclipseprojects.io"
		self.port = 1883
		self.companyList = json.load(open("../CompanyList.json"))['CompanyList']
		self.basicTopic = "IoTomatoes"
		self.topic_features = [ 
						"alertMeasureRange",
						"alertNoMessage",
						"ErrorReported"
						]
		self.topics = self.createTopics()
		self._paho_mqtt = PahoMQTT.Client(self.clientID, True)
		print("Topics : ")
		for top in self.topics:
			print(top, "\n")
							
		self.start()
		self._paho_mqtt.on_connect = self.OnConnect
		self._paho_mqtt.on_message = self.MessageReceived

	def createTopics(self):
		topics = []
		for top in self.topic_features:
			for comp in self.companyList:
				topics.append(f"{self.basicTopic}/FaultDetection/{comp['companyName']}/{top}")
				topics.append(f"{self.basicTopic}/ConsumptionManagement/{comp['companyName']}/ErrorReported")
		return topics

	def start (self):
		self._paho_mqtt.connect(self.broker, self.port)
		self._paho_mqtt.loop_start()
	
		for i in self.topics:
			self._paho_mqtt.subscribe(i, 2)

	def stop (self):
		for i in self.topics:
			self._paho_mqtt.unsubscribe(i)
		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()

	def OnConnect (self, paho_mqtt, userdata, flags, rc):
		print ("Connected to %s with result code: %d" % (self.broker, rc))

	def MessageReceived (self, paho_mqtt , userdata, msg):
		message = json.loads(msg.payload).get("message")
		print("Message received: ", message)

if __name__ == "__main__":
	fu = FakeUser()
	while True:
		pass