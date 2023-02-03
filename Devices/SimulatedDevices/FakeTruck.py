import json
import time

from iotomatoes_supportpackage.GPSgenerator import GPSgenerator
from iotomatoes_supportpackage.IoTDevice import IoTDevice

class SimTruck(IoTDevice):
    def __init__(self, DeviceInfo : dict):
        """Constructor of the simulated sensor. It initializes the sensor and
        the MQTT client, it registers the sensor to the ResourceCatalog and to the broker
        and it subscribes to the topics specified in the ResourceCatalog.
        Finally it starts the simulator of the ambient conditions."""

        self.tractor = GPSgenerator()
        self.tractor.shape(64)
        super().__init__(DeviceInfo, sensor = self)

    def get_position(self):
        """This function is used to get the temperature reading from the AmbientSimulator."""

        return self.tractor.get_position()

if __name__ == "__main__":
    try:
        settings = json.load(open("DeviceSettings.json"))
        IoTSensor = SimTruck(settings)
    except Exception as e:
        print(e)
    else:
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt or SystemExit:
                IoTSensor.close()