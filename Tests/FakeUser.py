import paho.mqtt.client as PahoMQTT
import json

class FakeUser():
	def __init__(self):
		self.clientID = "FakeUser"
		self.broker = "mqtt.eclipseprojects.io"
		self.port = 1883

		self.topics = ["IoTomatoes/FaultDetection/alertMeasureRange", "IoTomatoes/FaultDetection/alertNoMessage"]
		self._paho_mqtt = PahoMQTT.Client(self.clientID, True)
		
		self.start()
		self._paho_mqtt.on_connect = self.OnConnect
		self._paho_mqtt.on_message = self.MessageReceived

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
		print("Message received: ", msg.payload, "on topic: ", msg.topic)

if __name__ == "__main__":
	fu = FakeUser()
	while True:
		pass