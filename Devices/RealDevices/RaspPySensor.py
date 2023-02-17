import json
import time
import Adafruit_DHT

from iotomatoes_supportpackage import IoTDevice

sensor = Adafruit_DHT.DHT11


class RasPySensor(IoTDevice):
    def __init__(self, DeviceInfo: dict):
        """Constructor of the Raspberry Pi sensor. It will initialize the sensor and
        the MQTT client, it will register the sensor to the ResourceCatalog and to the broker 
        and it will subscribe to the topics specified in the ResourceCatalog."""

        super().__init__(DeviceInfo, sensor=self)

        self.pin = settings["PIN_IN"]

    def get_temperature(self):
        """This function is called periodically in order to get the sensor readings.
        It will publish the readings on the topics specified in the ResourceCatalog.

        In this example, the sensor is a DHT11 temperature and humidity sensor."""

        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, self.pin)

        return temperature

    def get_humidity(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, self.pin)

        return humidity


if __name__ == "__main__":
    try:
        settings = json.load(open("DeviceSettings.json"))
        IoTSensor = RasPySensor(settings)
    except Exception as e:
        print(e)
    else:
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt or SystemExit:
            IoTSensor.close()
