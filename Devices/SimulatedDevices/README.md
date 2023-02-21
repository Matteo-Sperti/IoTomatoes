# Simulated Devices

Code for the simulated devices. The simulated devices are used to test the IoTomatoes platform.

## Devices in Docker Containers

It is possible to simulate a devices in a container (closest solution to the real device).

1. Create a folder with the name of the device (e.g. [Device1](./Device1/))
2. Modify if necessary the [Dockerfile](./Device1/Dockerfile) (e.g. to install additional libraries)
3. Customize the [DeviceSettings.json](./Device1/DeviceSettings.json) configuration file
4. Add the device in the [docker-compose.yml](./docker-compose.yml) file
5. Run the compose file and the device will be started

### Configuration
In the [DeviceSettings.json](DeviceSettings.json) configuration file you must specify (same configuration file of a real device):
- **IoTomatoes_url:**: the IP address and the port of the IoTomatoes platform
- **CompanyName:** the Company name
- **fieldNumber:** the field number in which the sensor is installed
- the type of sensor or actuator (for istance ["humidity", "temperature"])

Optionally you can specify also:
- **Location** of the sensor (latitude and longitude)

## Devices Simulator

The device simulator is a python script that simulates a set of devices running on the host pc. 

In the [DevicesSimulatorSettings.json](DevicesSimulatorSettings.json) configuration file you must specify:
- the set of sensors and actuators.
- the measure time interval for each sensor
- the URL of the IoTomatoes platform

The script will create a random set of devices and will start to send measures to the IoTomatoes platform.

**[Code >>](DevicesSimulator.py)**