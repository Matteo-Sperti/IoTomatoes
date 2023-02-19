import requests
import time
import datetime
import json
import signal

from iotomatoes_supportpackage import BaseService

maxLimitTemp = datetime.time(23, 59, 0)
minLimitTemp = datetime.time(0, 0, 0)
weight = 0.75  # weight of the current measure in the average


class SmartIrrigation(BaseService):

    def __init__(self, settings: dict, controlPeriod: int = 60):
        """It initializes the service with its `settings (dict)`"""
        super().__init__(settings)

        self.controlPeriod = controlPeriod
        if "WeatherForecast_ServiceName" in settings:
            self.weatherToCall = settings["WeatherForecast_ServiceName"]

        if "MongoDB_ServiceName" in settings:
            self.mongoToCall = settings["MongoDB_ServiceName"]

        self._message = {
            "bn": "",
            "cn": "",
            "fieldNumber": "",
            "e": [{
                "n": "pump",
                "u": "/",
                "v": 0,
                "t": ""
            }]
        }

    def control(self):
        """It performs:
        1. Call to resource catalog -> to retrieve information about each field for each company
        2. Call to MongoDB to retrieve information about last hour measures (currentSoilMoisture)
            and previoius hour measures (previousSoilMoisture)
        3. Call to Weather forecast service to retrieve information about precipitation during the day
        With these information it performs a control strategy with an hysteresis law in order to send
        the command ON when the soil moisture mesaure decrease and is under a specific low threshold
        and to send command OFF in the opposite case"""

        companyList = self.getCompaniesList()

        for company in companyList:
            CompanyName = company["CompanyName"]

            for field in company["fieldsList"]:
                fieldID = field["fieldNumber"]
                plant = field["plant"]

                # EXTRACT ALL THE ACTUATOR TOPICS FOR THE SPECIFIC FIELD
                actuatorTopicsForField = self.getTopics(company, fieldID)

                if len(actuatorTopicsForField) == 0:
                    print("No actuator topics for the field ", fieldID)
                    continue

                minSoilMoisture, maxSoilMoisture, precipitationLimit = self.getPlantLimit(
                    plant)
                previousSoilMoisture, currentSoilMoisture = self.getMongoDBdata(
                    CompanyName, fieldID)
                if (previousSoilMoisture == None or currentSoilMoisture == None or
                        minSoilMoisture == None or maxSoilMoisture == None or precipitationLimit == None):
                    print("No previous or current soil moisture measure")
                    self.sendCommand(CompanyName, fieldID,
                                     actuatorTopicsForField, 0)
                    continue

                currentTime = datetime.datetime.now().time()
                soilMoistureForecast, dailyPrecipitationSum = self.callWeatherService(
                    CompanyName, currentTime.hour)
                if soilMoistureForecast == None or dailyPrecipitationSum == None:
                    print("No weather forecast available")
                    dailyPrecipitationSum = 0
                else:
                    currentSoilMoisture = round(
                        weight*currentSoilMoisture + (1-weight)*soilMoistureForecast, 2)

                # CONTROL ALGORITHM:
                print(
                    f"Performing control on: Company={CompanyName} field={fieldID}")
                if currentTime < minLimitTemp or currentTime > maxLimitTemp:
                    print("NO IRRIGATION TIME")
                    self.sendCommand(CompanyName, fieldID,
                                     actuatorTopicsForField, 0)
                else:
                    # PRECIPITATIONS CONTROL:
                    if dailyPrecipitationSum > precipitationLimit:  # soil too moist
                        print("IRRIGATION DOES NOT MAKE SENSE")
                        self.sendCommand(CompanyName, fieldID,
                                         actuatorTopicsForField, 0)
                    else:
                        print("IRRIGATION MAKE SENSE")
                        command = 0
                        # HYSTERESIS CONTROL LAW (SOILMOISTURE):
                        # After the precipitations control, we assume that soilMoisture increasing is related
                        # only to our irrigation and not also to possible external phenomena

                        print(f"OFF threshold={maxSoilMoisture}")
                        print(f"ON threshold={minSoilMoisture}")
                        print(
                            f"current value soil moisture={currentSoilMoisture}")
                        print(
                            f"previous value soil moisture={previousSoilMoisture}")

                        if currentSoilMoisture > previousSoilMoisture:
                            print("soilMoisture is increasing")
                            if currentSoilMoisture >= maxSoilMoisture:
                                print(
                                    f"""current soil moisture over/on the OFF limit: {currentSoilMoisture}>={maxSoilMoisture}""")
                                command = 0

                            else:
                                print(
                                    f"""current soil moisture under the OFF limit: {currentSoilMoisture}<{maxSoilMoisture}""")
                                command = 1

                        elif currentSoilMoisture < previousSoilMoisture:
                            print(f"soilMoisture is decreasing")
                            if currentSoilMoisture <= minSoilMoisture:
                                print(
                                    f"""current soil moisture under/on the ON limit: {currentSoilMoisture}<={minSoilMoisture}""")
                                command = 1

                            else:
                                print(
                                    f"""current soil moisture over the ON limit: {currentSoilMoisture}>{minSoilMoisture}""")
                                command = 0

                        else:
                            print("costant soil moisture")
                            if currentSoilMoisture > maxSoilMoisture:
                                command = 0

                            elif currentSoilMoisture < minSoilMoisture:
                                command = 1

                        self.sendCommand(CompanyName, fieldID,
                                         actuatorTopicsForField, command)

    def sendCommand(self, CompanyName: str, fieldID: int, topicList: list, command: int):
        message = self._message.copy()

        print(f"\nActuators topics list= {topicList}")
        print(
            f"Setting the pumps of field {fieldID} of company {CompanyName} to {'ON' if command==1 else 'OFF'}")
        for singleTopic in topicList:
            message["bn"] = self.EndpointInfo["serviceName"]
            message["cn"] = CompanyName
            message["fieldNumber"] = fieldID
            message["e"][-1]["v"] = command
            message["e"][-1]["t"] = time.time()

            commandTopic = str(singleTopic)
            self._MQTTClient.myPublish(commandTopic, message)

    def getTopics(self, company: dict, fieldNumber: int):
        """Return the list of the subscribed topics for a field in the company"""
        topics = []
        for device in company["devicesList"]:
            if fieldNumber == device["fieldNumber"] and device["isActuator"] == True:
                if "pump" in device["actuatorType"]:
                    topics.append(
                        f"{company['CompanyName']}/{fieldNumber}/{device['ID']}/pump")

        return topics

    def getPlantLimit(self, plant: str):
        """Return the plant information from the MongoDB service"""

        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None, None, None

        try:
            r = requests.get(f"{mongoDB_url}/plant",
                             params={"PlantName": plant})
            r.raise_for_status()
            plantInfo = r.json()
        except:
            print("ERROR: MongoDB service not found!")
            return None, None, None
        else:
            minSoilMoisture = plantInfo["soilMoistureLimit"]["min"]
            maxSoilMoisture = plantInfo["soilMoistureLimit"]["max"]
            precipitationLimit = plantInfo["precipitationLimit"]["max"]

            print("Retrieved plant limits from MongoDB service!")
            return minSoilMoisture, maxSoilMoisture, precipitationLimit

    def getMongoDBdata(self, CompanyName: str, fieldID: int):
        """Return the average soil moisture of the last controlPeriod seconds from the MongoDB service

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `fieldID (int)`: ID of the field.
        """

        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)

        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None, None

        try:
            params = {"Field": fieldID,
                      "start_date": time.time() - self.controlPeriod,
                      "end_date": time.time(),
                      "measure": "soilMoisture"}
            r = requests.get(f"{mongoDB_url}/{CompanyName}/avg", params=params)
            r.raise_for_status()
            dict_ = r.json()
            previousSoilMoisture = dict_["Average"]

            params = {"Field": fieldID,
                      "start_date": time.time() - self.controlPeriod,
                      "end_date": time.time(),
                      "measure": "soilMoisture"}
            r = requests.get(f"{mongoDB_url}/{CompanyName}/avg", params=params)
            r.raise_for_status()
            dict_ = r.json()
            currentSoilMoisture = dict_["Average"]
        except:
            return None, None
        else:
            return previousSoilMoisture, currentSoilMoisture

    def callWeatherService(self, CompanyName: str, hour):
        """It gets precipitations informations from weather forecast service and extract:
            - daily precipitation sum
            - soil moisture forecast
            from the received json file
            """
        weatherForecast_url = self.getOtherServiceURL(self.weatherToCall)
        if weatherForecast_url == None or weatherForecast_url == "":
            print("ERROR: Weather Forecast service not found!")
            return None, None

        try:
            weatherService_data = requests.get(
                f"{weatherForecast_url}/{CompanyName}/irrigation")
            weatherService_data.raise_for_status()
            weatherService_data = weatherService_data.json()
        except:
            print("ERROR: Weather Forecast service not available!")
            return None, None
        else:
            daily_precipitation_sum = weatherService_data["daily"]["precipitation_sum"][0]
            soil_moisture_forecast = weatherService_data["hourly"]["soil_moisture_3_9cm"][hour]

            print("Retrieved weather forecast from Weather Forecast service!")
            return soil_moisture_forecast, daily_precipitation_sum


def sigterm_handler(signal, frame):
    irrigation.stop()
    print("SmartIrrigation stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open("SmartIrrigationSettings.json", 'r'))
    except FileNotFoundError:
        print("ERROR: files not found")
    else:
        controlTimeInterval = settings["controlTimeInterval"]
        irrigation = SmartIrrigation(settings, controlTimeInterval)

        while True:
            irrigation.control()
            time.sleep(controlTimeInterval)
