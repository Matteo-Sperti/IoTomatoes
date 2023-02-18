# IoTomatoes

IoT project for smart-agriculture.
IoTomatoes provides support to agri-service providers in order to enhance productivity, 
optimize power consumption, and minimize environmental impact.

The proposed IoT platform integrates different IoT devices in order to provide a suitable control strategy and data analysis for agricultural holdings management and grow different types of crops. It also guarantees standardized communication interfaces (REST and MQTT) to easily communicate with pre-existing sensors.

The main features provided by the platform will be:
- Consumption management;
- Machineries geolocalization;
- Irrigation and lighting control;
- Environment and soil data analysis;
- Unified interfaces (REST Web Services and MQTT);
- End-users’ maintenance and awareness.

# Installation

The required packages to run the IoT platform are:

- [Python 3.x](https://www.python.org/)
- [CherryPy](https://cherrypy.dev/)
- [paho-mqtt](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [docker](https://www.docker.com/)
- [requests](https://requests.readthedocs.io/en/latest/#)
- [pymongo](https://pymongo.readthedocs.io/en/stable/)
- [NumPy](https://numpy.org/)
- [matplotlib](https://matplotlib.org/)
- [gpxpy](https://pypi.org/project/gpxpy/)
- [folium](https://python-visualization.github.io/folium/)

Moreover it is suggested to install the support package [IoTomatoes_SupportPackage](./IoTomatoes_SupportPackage/README.md) that contains some useful functions to simplify the development of the IoT devices on your host PC.

    python -m pip install -i https://test.pypi.org/simple/ IoTomatoes_SupportPackage --no-deps

# Contents

- the [IoTomatoes_SupportPackage](./IoTomatoes_SupportPackage/README.md) package: it contains some useful functions to simplify the development of the IoT devices;

- the [IoTomatoes_Platform](./IoTomatoes_Platform/README.md) folder: it contains the IoTomatoes IoT platform:

- the [Devices](./Devices/README.md) folder: it contains the IoT devices developed for the project;

- the [Doc](./Doc/README.md) folder: it contains some documentation about the project;

- the [Tests](./Tests/README.md) folder: it contains some tests for the IoT platform.

# Disclaimer

This project is a research project and it is not intended for commercial use. The authors are not responsible for any damage caused by the use of this software. The security of the IoT platform is not guaranteed as it is not the main focus of the project.

# Authors

- [Matteo Sperti](https://github.com/Matteo-Sperti)
- [Federico Moscato](https://github.com/JMFede)
- [Andrea Usai](https://github.com/Andrechief98)
- [Luca Zanetti](https://github.com/lucazanett)

