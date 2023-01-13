import paho.mqtt.client as mqtt
import time
import json
from statistics import mean
import datetime

class Pump:

    def __init__(self):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""

        self.serviceID="pump"
        self.topic="IoTomatoes/+/+/+/pump" #IoTomatoes/companyName/field/actuatorID/actuatorType
        self.broker="test.mosquitto.org"
        self.port=1883

        
        self.service_mqtt=mqtt.Client(self.serviceID,True)

        #CALLBACK
        self.service_mqtt.on_connect=self.myOnConnect
        self.service_mqtt.on_message=self.myOnMessage

    def start(self):
        """Connects and subscribes the service to the broker"""
        self.service_mqtt.connect(self.broker,self.port)
        self.service_mqtt.loop_start()
        self.service_mqtt.subscribe(self.topic,2)
    
    def myOnConnect(self,client,userdata,flags,rc):
        """It provides information about Connection result with the broker"""
        dic={
            "0":f"Connection successful to {self.broker}",
            "1":f"Connection to {self.broker} refused - incorrect protocol version",
            "2":f"Connection to {self.broker} refused - invalid client identifier",
            "3":f"Connection to {self.broker} refused - server unavailable",
        }
             
        print(dic[str(rc)])

    def myOnMessage(self,client,userdata,message):
        """Riceives command from smart irrigation"""
        self.payload=json.loads(message.payload)
        print(self.payload)

    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()

if __name__=="__main__":

    
    pompa=Pump()
    pompa.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            pompa.stop()
            break
    