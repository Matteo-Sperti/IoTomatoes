import json
from iotomatoes_supportpackage.AmbientSimulator import AmbientSimulator
from iotomatoes_supportpackage.IoTDevice import IoTDevice

class SimDevice(IoTDevice):
    def __init__(self, DeviceInfo : dict):
        """Constructor of the simulated sensor. It will initialize the sensor and
        the MQTT client, it will register the sensor to the ResourceCatalog and to the broker
        and it will subscribe to the topics specified in the ResourceCatalog.
        
        Finally it start the simulator of the ambient conditions."""

        super().__init__(DeviceInfo, sensor = self, actuator = self)
        self._Ambient = AmbientSimulator()
            
    def setActuator(self, actuator : str, state : bool):
        """This function is used to set the state of an actuator in the AmbientSimulator."""
        if state:
            print(f"Resource {self.ID}: {actuator} turned ON")
        else:
            print(f"Resource {self.ID}: {actuator} turned OFF")
        self._Ambient.setActuator(actuator, state)

    def get_temperature(self):
        """This function is used to get the temperature reading from the AmbientSimulator."""

        return self._Ambient.get_temperature()

    def get_humidity(self):
        """This function is used to get the humidity reading from the AmbientSimulator."""

        return self._Ambient.get_humidity()

    def get_light(self):
        """This function is used to get the light reading from the AmbientSimulator."""

        return self._Ambient.get_light()

    def get_soilMoisture(self):
        """This function is used to get the soil moisture reading from the AmbientSimulator."""
        
        return self._Ambient.get_soilMoisture()

if __name__ == "__main__":
    try:
        settings = json.load(open("DeviceSettings.json"))
        IoTSensor = SimDevice(settings)

    except Exception as e:
        print(e)