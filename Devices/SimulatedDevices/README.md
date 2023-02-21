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
- **IoTomatoes_url:**: the IP address and the port of the IoTomatoes platform
- **CompanyName:** the Company name
- **field:** the field number in which the sensor is installed
- the type of sensor or actuator (for istance ["humidity", "temperature"])

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

The script will create a random set of devices and will start to send measures to the IoTomatoes platform.

**[Code >>](DevicesSimulator.py)**