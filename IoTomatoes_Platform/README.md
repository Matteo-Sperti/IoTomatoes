# IoT Platform

The proposed IoT platform for Smart Farming is built on the base of the microservices design pattern. It will basically exploit 2 types of communication paradigms:
- **PUBLISH/SUBSCRIBE:** based on the usage of the MQTT protocol;
- **REQUEST/RESPONSE:** based on REST Web Services.

![plot](../Doc/Schema_platform.png)

## Launcher
The **[docker-compose.yml](./docker-compose.yml)** file is a script that allows to build and run all the microservices of the IoT platform in a single command. In the configuration it uses a bridge network to allow the communication between the microservices. It also uses the host network to allow the communication between the services and the devices on the Raspberry Pi board.

Together with all the microservices, it also launches:
- the NGINX server that allow the communication between the services in the platform and the external world.
- the MOSQUITTO broker that works as a MQTT broker to allow the communication between the services in the platform and the external devices.

## Resource Catalog
It works as a REST Web Service and provides information about endpoints (URI and MQTT topics) of all the devices in the platform. Therefore, each IoT device will need to be registered and must be able to update it periodically.

**[Code >>](./ResourceCatalog/)**  

**[Example of ResourceCatalog >>](./Doc/ResourceCatalog.json)**

## Service Catalog
It works as a REST Web Service and provides information about endpoints (URI and MQTT topics) of all the REST Web Services (including the Resource Catalog) in the platform. 

**[Code >>](./ServiceCatalog/)**  

**[Example of ServiceCatalog >>](./Doc/ServiceCatalog.json)**

**[Service Catalog Settings >>](./Doc/ServiceCatalogSettings.json)**

## Database Connector
It works as a REST Web Service and provides the possibility to store and retrieve data from the MongoDB database. It also exploits the MQTT protocol to receive messages from the different sensors and microservices.

**[Code >>](./MongoDBConnector/)**  

## Telegram Bot
It is a service that allows the integration of the IoT infrastructure into Telegram platform. 
This service will allow the user to manage his company through Telegram.
It will exploit REST Web Services to retrieve IoT devices data from the Database Connector or from the Data Visualizer. Moreover, it will exploit the MQTT protocol to receive messages and alarms from the different microservices.

**[Code >>](./TelegramBot/)**  

## Dashboard
It is used to retrieve and visualize data from IoT devices of the platform through a MQTT subscriber. It will be realized through Node-RED.

## Fault Detection System 
This service performs different data control strategies in order to ensure that each IoT device data is consistent and identify some possible failures and malfunctions in the platform.

**[Code >>](./FaultDetectionService/)**  

## Consumption Management
It will retrieve and store data about main resources consumption (water, average electrical power, seed and fertilizer) from related REST Web Services. Through this service the company can have a picture of its consumption (and so of its outgoings) and can reduce the impact on the environment.

**[Code >>](./ConsumptionManager/)** 

## Smart irrigation
This service is used to automatically manage the irrigation plant of the farm.

**[Code >>](./SmartIrrigation/)**  

## Smart lighting
This service retrieves sensors data already processed by the MongoDBConnector, the weather Forecast and integrate everything to obtain an autonomous control of the lighting system.

**[Code >>](./SmartLighting/)**   

## Weather Forecast
This service uses third-party API to retrieve the weather information and forecast for the farm area. Moreover, it exploits the possibility to include in the analysis data coming from pre-existing weather stations (further updates of the project)

**[Code >>](./WeatherForecast/)**  

## Localization
This service uses third-party API and GPS present in all the machineries to localize them in the field and track their movement during the work hours. With this solution, the company can easily keep track of the work done and plan next operations for the following days.

**[Code >>](./Localization/)**  