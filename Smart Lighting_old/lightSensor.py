import paho.mqtt.client as mqtt
import json
import time
import numpy.random as numpy

class Sensor:

    def __init__(self, sensorID, companyName, topic, broker, port):
        self.sensorID=sensorID
        self.companyName=companyName
        self.topic=topic
        self.broker=broker
        self.port=port
        self.message={
            "companyName":self.companyName,
            "bn":self.sensorID,
            "field":1,
            "e": {
                "name":"Light",
                "value":None,
                "unit": "lx",       #1 lux = 1 lumen/m2
                "timestamp": None
            }
        }
    
        self.sensor_mqtt=mqtt.Client(self.sensorID,True)

        #CALL BACK
        self.sensor_mqtt.on_connect=self.myOnConnect
        


    def start(self):
        """Connects fake light sensor to the broker"""
        self.sensor_mqtt.connect(self.broker,self.port)
        self.sensor_mqtt.loop_start()

    def stop(self):
        """Disconnects fake light sensor from the broker"""
        self.sensor_mqtt.loop_stop()
        self.sensor_mqtt.disconnect()
 
    def myOnConnect(self,client,userdata,flags,rc):
        dic={
            "0":f"Connection successful to {self.broker}",
            "1":f"Connection to {self.broker} refused - incorrect protocol version",
            "2":f"Connection to {self.broker} refused - invalid client identifier",
            "3":f"Connection to {self.broker} refused - server unavailable",
        }
             
        print(dic[str(rc)])

    def senData(self,measure):
        """Fake light sensor publishes random data to the broker"""
        message=self.message
        message["e"]["value"]=measure
        message["e"]["timestamp"]=time.time()
        self.sensor_mqtt.publish(self.topic,json.dumps(message),2)
        print(f"Published\n {message}")


if __name__=="__main__":
    
    broker="test.mosquitto.org"
    port=1883

    sensorList=[]
    sensorCompanyName=["Andrea","Federico"]
    sensorIDtopic=["sensor1","sensor2"]
    
    for j in sensorCompanyName:
        for i in sensorIDtopic:
            sensor=Sensor(i,j,"IoTomatoes/"+f"{j}"+"/field1/light/"+f"{i}"+"/measure",broker,port)
            sensor.start()
            sensorList.append(sensor)

    lista1=range(30000,80000,5000)
    lista2=range(80000,30000,-5000)
    while True:
        for measure in lista1:
            for i in sensorList:
                i.senData(measure)
            time.sleep(5)
        for measure in lista2:
            for i in sensorList:
                i.senData(measure)
            time.sleep(5)
