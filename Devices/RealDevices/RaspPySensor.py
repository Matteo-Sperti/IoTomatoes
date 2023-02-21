import json
import time
import Adafruit_DHT
import RPi.GPIO as GPIO

from iotomatoes_supportpackage import IoTDevice

sensor = Adafruit_DHT.DHT11


class RasPySensor(IoTDevice):
    def __init__(self, DeviceInfo: dict):
        """Constructor of the Raspberry Pi sensor. It will initialize the sensor and
        the MQTT client, it will register the sensor to the ResourceCatalog and to the broker 
        and it will subscribe to the topics specified in the ResourceCatalog."""

        self.pinIN = settings["PIN_IN"]
        self.pinOUT = settings["PIN_OUT"]

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(self.pinOUT, GPIO.OUT)

        super().__init__(DeviceInfo, sensor=self, actuator=self)


    def get_temperature(self):
        """This function is called periodically in order to get the sensor readings.
        It will publish the readings on the topics specified in the ResourceCatalog.

        In this example, the sensor is a DHT11 temperature and humidity sensor."""

        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, self.pinIN)

        return temperature

    def get_humidity(self):
        # Try to grab a sensor reading.  Use the read_retry method which will retry up
        # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
        humidity, temperature = Adafruit_DHT.read_retry(sensor, self.pinIN)

        return humidity

    def setActuator(self, actuator: str, state: bool):
        """This function is used to set the state of an actuator in the AmbientSimulator."""

        if actuator == self.actuatorType[0]:
            print(f"Resource {self.ID}: {actuator} turned {'ON' if state else 'OFF'}\n")
            GPIO.output(self.pinOUT,state)

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
