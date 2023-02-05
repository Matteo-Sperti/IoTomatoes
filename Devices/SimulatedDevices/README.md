# Simulated Devices

Code for the simulated devices. The simulated devices are used to test the IoTomatoes platform.

## Single Device

It is possible to simulate a single device in a container (closest solution to the real device).

1. Create a folder with the name of the device (e.g. [Device1](./Device1/))
2. Modify if necessary the [Dockerfile](./Device1/Dockerfile) (e.g. to install additional libraries)
3. Customize the [DeviceSettings.json](./Device1/DeviceSettings.json) configuration file
4. Add the device in the [docker-compose.yml](../../docker-compose.yml) file
5. Run the platform with all the other microservices

### Configuration
In the [DeviceSettings.json](DeviceSettings.json) configuration file you must specify (same configuration file of a real device):
- **ServiceCatalog_url:**: the IP address of the IoTomatoes platform
- **CompanyName:** the Company name
- **field:** the field number in which the sensor is installed
- the type of sensor or actuator (in this case ["humidity", "temperature"])

Moreover you must add in the configuration file any additional information about the sensor or actuator. in this example:
- **PIN_IN:** the PIN number of the Raspberry Pi where the sensor is connected
- **measureTimeInterval:** the time interval between two measures

Optionally you can specify also:
- **Location** of the sensor (latitude and longitude)

## Multiple Devices

It is possibile to run multiple devices (each one in a different container) using the [docker-compose.yml](docker-compose.yml) file. It runs all the five devices in the [Simulated Devices](./) folder. For each of them it is possible to customize the configuration file and the Dockerfile. All the devices uses the host network.

## Devices Simulator

The device simulator is a python script that simulates a set of devices. 

In the [DevicesSimulatorSettings.json](DevicesSimulatorSettings.json) configuration file you must specify:
- the set of sensors and actuators.
- the measure time interval for each sensor
- the URL of the IoTomatoes platform
- the System Token of the IoTomatoes platform used to access a priori some information about a company (e.g. its location)

The script will create a ranodm set of devices and will start to send measures to the IoTomatoes platform.

**[Code >>](DevicesSimulator.py)**