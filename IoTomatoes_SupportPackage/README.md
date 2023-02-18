# IoTomatoes Support package

Python Support package for the IoT platform for smart agriculture.

## Requirements

- [Python 3.x](https://www.python.org/)
- [NumPy](https://numpy.org/)
- [paho-mqtt](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [requests](https://requests.readthedocs.io/en/latest/#)

## Installation

To install the package, run the following command:

    python3 -m pip install -i https://test.pypi.org/simple/ IoTomatoes-SupportPackage --no-deps


## Contents

### AmbientSimulator

This python class simulates the ambient conditions of the field. It is used to test the IoT platform.
It subscribes to the actuators' topics and modifies the ambient conditions accordingly.
Moroever it add some noise to the ambient conditions to simulate the real conditions.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/AmbientSimulator.py)**

### GPSgenerator

This python class generates a tuple of coordinates (latitude, longitude) according for simulate the GPS position of a tractor. It exploits a simple random walk algorithm to generate the coordinates. The coordinates are generated starting from the company's location.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/GPSgenerator.py)**

### DeviceManager

This python module contains some useful functions to check the devices status.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/DeviceManager.py)**

### BaseResource

This python module contains the class for the base resource of the platform. It provides the function to construct the resource dictionary and to interact with the catalog of the platform. 

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/BaseResource.py)**

### BaseService

This python module contains the class for the base service of the platform. It provides the function to construct the service dictionary and to interact with the catalog of the platform.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/BaseService.py)**

### ItemInfo

This python module contains useful functions to get information from a dictionary in the platform according to the specification of the catalog.
It also contains the class for constructing the information dictionary of a device starting from few parameters.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/ItemInfo.py)**

### MyException

This python module contains the class for the custom exceptions of the platform.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/MyException.py)**

### MyIDGenerator

This python module contains the class for the ID generator of the platform.
It generates unique integer IDS for each instance of this class.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/MyIDGenerator.py)**

### MyThread

This python module contains the class for the custom threads of the platform.

**[Code >>](https://github.com/Matteo-Sperti/IoTomatoes_SupportPackage/src/MyThread.py)**

## Authors

- [Matteo Sperti](https://github.com/Matteo-Sperti)
- [Federico Moscato](https://github.com/JMFede)
- [Andrea Usai](https://github.com/Andrechief98)
- [Luca Zanetti](https://github.com/lucazanett)

