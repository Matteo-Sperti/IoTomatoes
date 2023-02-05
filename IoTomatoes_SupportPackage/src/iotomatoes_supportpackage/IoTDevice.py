import time
from iotomatoes_supportpackage.BaseResource import BaseResource
from iotomatoes_supportpackage.MyThread import MyThread
from iotomatoes_supportpackage.ItemInfo import publishedTopics, actuatorType

class IoTDevice(BaseResource):
    def __init__(self, DeviceInfo : dict, sensor = None, actuator = None):
        """Constructor of a generic device. It will initialize the device and
        the MQTT client, it will register itself to the ResourceCatalog and to the broker
        and it will subscribe to the topics specified in the ResourceCatalog.
        
        It will also initialize the thread used to get the sensor readings.
        
        Arguments:\n
        `DeviceInfo` : dictionary containing the information about the device.\n
        `sensor` : sensor object used to get the sensor readings. 
        It is None if the device is not a sensor.
        It must have the `get_<measure>` function for each measure specified in the ResourceCatalog.\n
        `actuator` : actuator object used to set the actuator state.
        It is None if the device is not an actuator.
        It must have the `setActuator` function.
        """

        super().__init__(DeviceInfo)

        if self.isActuator:
            if actuator is None:
                raise Exception("Actuator not specified")
            self._Actuator = actuator

        if self.isSensor:
            if sensor is None:
                raise Exception("Sensor not specified")
            if "measureTimeInterval" in DeviceInfo:
                self._measureTimeInterval = DeviceInfo["measureTimeInterval"]
            else:
                self._measureTimeInterval = 5
            self._message={
                "cn" : self.CompanyName,
                "bn" : self.ID,
                "fieldNumber" : self.field,
                "e" : [{
                    "n": "",
                    "v": None,
                    "u": "",       
                    "t": None
                }]
            }
            self._SendThread = MyThread(self.get_measures, self._measureTimeInterval, sensor)

    def close(self):
        """This function is used to close the MQTT client and the thread 
        used to get the sensor readings."""

        self.stop()
        if self.isSensor:
            self._SendThread.stop()

    def notify(self, topic, msg):
        """This function is used to notify the device when a message is received.
        If the device is an actuator it will set the actuator state.
        """
        print(f"Resource {self.ID} received message on topic {topic}\n")

        if not self.isActuator:
            print("Resource is not an actuator.\n"
                    f"Topic: {topic}\n"
                    f"Message: {msg}")
        else:
            actuator_info = actuatorType(self._EndpointInfo)
            actuator_topic = topic.split("/")[-1]

            if actuator_topic not in actuator_info:
                print(f"Resource {self.ID}: {actuator_topic} not found")
            else:
                try:
                    state = msg["e"][0]["v"]
                except KeyError:
                    print("Message not valid")
                else:
                    if state == 0:
                        self._Actuator.setActuator(actuator_topic, False)
                    elif state == 1:
                        self._Actuator.setActuator(actuator_topic, False)
                    else:
                        print(f"Resource {self.ID}: {actuator_topic} state not valid")

            
    def get_measures(self, sensor):
        """This function is called periodically in order to get the sensor readings.
        It will publish the readings on the topics specified in the ResourceCatalog.
        """

        for topic in publishedTopics(self._EndpointInfo):
            measureType = topic.split("/")[-1]
            
            if measureType == "temperature":
                msg = self.construct_message(measureType, "C")
                v = sensor.get_temperature()
            elif measureType == "humidity":
                msg = self.construct_message(measureType, "%")
                v = sensor.get_humidity()
            elif measureType == "light":
                msg = self.construct_message(measureType, "lx")
                v = sensor.get_light()
            elif measureType == "soilMoisture":
                msg = self.construct_message(measureType, "%")
                v = sensor.get_soilMoisture()
            elif measureType == "position":
                msg = self.construct_message(measureType, "°")
                v = sensor.get_position()
            else:
                continue
                
            if v is not None:
                msg["e"][-1]["v"] = v
                self._MQTTClient.myPublish(topic, msg)
    
    def construct_message(self, measure : str, unit : str) :
        """This function is used to construct the message to be published on the topics."""

        msg = self._message.copy()
        msg["e"][-1]["n"] = measure
        msg["e"][-1]["v"] = 0
        msg["e"][-1]["t"] = time.time()
        msg["e"][-1]["u"] = unit
        return msg