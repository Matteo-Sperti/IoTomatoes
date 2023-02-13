import json
import time
import signal

from iotomatoes_supportpackage.GPSgenerator import GPSgenerator
from iotomatoes_supportpackage.IoTDevice import IoTDevice


class SimTruck(IoTDevice):
    def __init__(self, DeviceInfo: dict):
        """Constructor of the simulated sensor. It initializes the sensor and
        the MQTT client, it registers the sensor to the ResourceCatalog and to the broker
        and it subscribes to the topics specified in the ResourceCatalog."""
        
        self.platform_url = DeviceInfo["IoTomatoes_url"]
        self.CompanyName = DeviceInfo["CompanyName"]
        self.tractor = GPSgenerator(self.platform_url, self.CompanyName)
        super().__init__(DeviceInfo, sensor=self)

    def get_position(self):
        """This function is used to get the GPS reading from the GPSgenerator."""

        return self.tractor.get_position()


def sigterm_handler(signal, frame):
    """Handler for the SIGTERM signal. It closes the MQTT client and the sensor."""

    IoTSensor.close()
    IoTSensor.tractor.TruckStop()
    print("Truck stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open("TruckSettings.json", "r"))
        IoTSensor = SimTruck(settings)
    except Exception as e:
        print(e)
    else:
        while True:
            time.sleep(10)
