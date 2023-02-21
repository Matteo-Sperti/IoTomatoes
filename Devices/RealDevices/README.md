# Real Sensor example

Code to insert a real sensor or actuator in the IoT platform.

In this example the RaspberryPy must be connected to a DHT11 temperature and humidity sensor.
The board is connected also to a led to simulate an actuator.

## Requirements
On your RaspberryPy you must install:
- [Python 3.x](https://www.python.org/)
- [paho-mqtt](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [requests](https://requests.readthedocs.io/en/latest/#)

## Installation

Copy in the same folder in the Raspberry Pi:
- [DeviceSettings.json](DeviceSettings.json)
- [RealRaspPySensor.py](RealRaspPySensor.py)

Install the requirements and the IoT support package:

    python -m pip install -i https://test.pypi.org/simple/ IoTomatoes_SupportPackage --no-deps

## Configuration
In the [DeviceSettings.json](DeviceSettings.json) configuration file you must specify:
- **IoTomatoes_url:**: the IP address and the port of the IoTomatoes platform
- **CompanyName:** the Company name
- **fieldNumber:** the field number in which the sensor is installed
- the type of sensor or actuator (in this case ["humidity", "temperature"])

Moreover you must add in the configuration file any additional information about the sensor or actuator. in this example:
- **PIN_IN:** the PIN number of the Raspberry Pi where the sensor is connected
- **PIN_OUT** the PIN number of the Raspberry Pi where the actuator is connected
- **measureTimeInterval:** the time interval between two measures

Optionally you can specify also:
- **Location** of the sensor (latitude and longitude)