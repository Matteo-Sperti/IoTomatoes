# Real Sensor example

Code to insert a real sensor or actuator in the IoT platform.

In this example the RaspberryPy must be connected to a DHT11 temperature and humidity sensor.

## Requirements
On your RaspberryPy you must install:
- [Python 3.x](https://www.python.org/)
- [paho-mqtt](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [requests](https://requests.readthedocs.io/en/latest/#)

## Configuration
In the [DeviceSettings.json](DeviceSettings.json) configuration file you must specify:
- **ServiceCatalog_url:**: the IP address of the IoTomatoes platform
- **CompanyInfo:** the Company information ("CompanyName" and "CompanyToken")
- **field:** the field number in which the sensor is installed
- the type of sensor or actuator (in this case ["humidity", "temperature"])

Moreover you must add in the configuration file any additional information about the sensor or actuator. in this example:
- **PIN_IN:** the PIN number of the RaspberryPy where the sensor is connected
- **measureTimeInterval:** the time interval between two measures

Optionally you can specify also:
- **Location** of the sensor (latitude and longitude)

## Installation

Copy in the same folder in the RaspberryPy:
- [DeviceSettings.json](DeviceSettings.json)
- [RealRaspPySensor.py](RealRaspPySensor.py)
- [MyExceptions.py](../../SupportClasses/MyExceptions.py)
- [ItemInfo.py](../../SupportClasses/ItemInfo.py)
- [GenericEndpoint.py](../../SupportClasses/GenericEndpoint.py)