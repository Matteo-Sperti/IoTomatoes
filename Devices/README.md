# Devices

This directory contains the code for the devices used in the project.
The idea is that each Raspberry Pi works as a device connector integrating the low-level technology of sensors  and actuators into the platform. The Raspberry Pi board communicates using low-energy communication protocols with temperature, humidity, air quality, solar radiations, soil moisture sensors located in the field, to retrieve environmental and soil information, or with leds and pumps. It communicates with the Catalog through REST and it works as a MQTT publisher to send the data collected, or as a MQTT subscriber to receive the actuation commands. It can be also used to integrate pre-existing sensors in the platform.

## [Real Device](./RealDevice/)

This directory contains the code for the real device used in the project. Every devices (both sensors and actuators) must be deployed on a Raspberry Pi board.

**[Read more >>](./RealDevices/README.md)**

## [Simulated Device](./SimulatedDevice/)

In this directory there is the code for the simulated devices. They are used to test the platform without the need to deploy the real devices.

**[Read more >>](./SimulatedDevices/README.md)**