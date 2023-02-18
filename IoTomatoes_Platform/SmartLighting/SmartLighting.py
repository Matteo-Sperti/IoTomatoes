import requests
import time
import datetime
import json
import signal

from iotomatoes_supportpackage import BaseService


class SmartLighting(BaseService):

    def __init__(self, settings: dict, controlPeriod: int = 60):
        """It initializes the service with the `settings (dict)`."""

        super().__init__(settings)
        self.controlPeriod = controlPeriod
        if "WeatherForecast_ServiceName" in settings:
            self.weatherToCall = settings["WeatherForecast_ServiceName"]

        if "MongoDB_ServiceName" in settings:
            self.mongoToCall = settings["MongoDB_ServiceName"]

        self._message = {
            "bn": self.EndpointInfo["serviceName"],
            "cn": "",
            "fieldNumber": "",
            "e": [{
                "n": "led",
                "u": "/",
                "v": 0,
                "t": ""
            }]
        }

    def control(self):
        """It performs:
        1. Call to resource catalog -> to retrieve information about each field for each company
        2. Call to MongoDB to retrieve information about last hour measures (currentLigh) and previous hour measures 
          (previousLight)
        3. Call to Weather forecast service to retrieve information about current cloudcover percentage, light, 
        sunrise hour and sunset hour. 

        With these information it integrates the forecast light with sensor measures and performs a simple control 
        strategy to check if the light is under a fixed threshold"""

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

                minLight, _ = self.getPlantLimit(plant)
                currentLight = self.getMongoDBdata(CompanyName, fieldID)
                if currentLight == None or minLight == None:
                    print("No previous or current soil moisture measure")
                    self.sendCommand(CompanyName, fieldID,
                                     actuatorTopicsForField, 0)
                    continue

                currentTime = datetime.datetime.now().time()
                cloudCover, lightForecast, Sunrise, Sunset = self.callWeatherService(
                    CompanyName, currentTime.hour)
                if cloudCover == None or lightForecast == None or Sunrise == None or Sunset == None:
                    print("No weather forecast available")
                    # default values
                    Sunrise = datetime.time(6, 0, 0)
                    Sunset = datetime.time(18, 0, 0)
                    cloudCover = 100
                else:
                    currentLight = round(
                        0.75*currentLight + 0.25*lightForecast, 2)

                # CONTROL ALGORITHM:
                # The control algorithm is scheduled on day time (between sunrise and sunset) and if the cloud cover is
                # higher than 60%.
                print(
                    f"Performing control on: Company={CompanyName} field={fieldID}")
                if currentTime < Sunrise or currentTime > Sunset:
                    print("IT'S NIGHT, NO LIGHTING TIME")
                    self.sendCommand(CompanyName, fieldID,
                                     actuatorTopicsForField, 0)
                else:
                    # CLOUDCOVER CONTROL
                    if cloudCover < 60:
                        print("No cloud cover, no lighting needed")
                        self.sendCommand(CompanyName, fieldID,
                                         actuatorTopicsForField, 0)
                    else:
                        command = 0
                        print("Cloud cover, lighting needed")
                        print(f"ON/OFF threshold={minLight}")
                        print(f"current value light={currentLight}")

                        if currentLight <= minLight:
                            command = 1
                        else:
                            command = 0

                        self.sendCommand(CompanyName, fieldID,
                                         actuatorTopicsForField, command)

    def sendCommand(self, CompanyName: str, fieldID: int, topicList: list, command: int):
        """It sends the command to the actuators of the field"""

        message = self._message.copy()

        print(f"\nActuators topics list= {topicList}")
        print(
            f"Setting the leds of field {fieldID} of company {CompanyName} to {'ON' if command==1 else 'OFF'}")
        for singleTopic in topicList:
            message["cn"] = CompanyName
            message["fieldNumber"] = fieldID
            message["e"][-1]["v"] = command
            message["e"][-1]["t"] = time.time()

            commandTopic = str(singleTopic)
            self._MQTTClient.myPublish(commandTopic, message)

    def getTopics(self, company, fieldNumber: int):
        """Return the list of the subscribed topics for all the LED actuator in a
          field in the company"""

        topics = []
        for device in company["devicesList"]:
            if fieldNumber == device["fieldNumber"] and device["isActuator"] == True:
                if "led" in device["actuatorType"]:
                    topics.append(
                        f"{company['CompanyName']}/{fieldNumber}/{device['ID']}/led")

        return topics

    def getPlantLimit(self, plant: str):
        """Return the min and max light limit for the plant from the MongoDB service"""

        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None, None

        try:
            r = requests.get(f"{mongoDB_url}/plant",
                             params={"PlantName": plant})
            r.raise_for_status()
            plantInfo = r.json()
        except:
            print("ERROR: MongoDB service not found!")
            return None, None
        else:
            minLightLimit = plantInfo["lightLimit"]["min"]
            maxLightLimit = plantInfo["lightLimit"]["max"]
            print("Retrieved plant limits from MongoDB service!")
            return minLightLimit, maxLightLimit

    def getMongoDBdata(self, CompanyName: str, fieldID: int):
        """Return the average soil moisture of the last controlPeriod seconds from the MongoDB service

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `fieldID (int)`: ID of the field.
        """

        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)

        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None

        try:
            params = {"Field": fieldID,
                      "start_date": time.time() - self.controlPeriod,
                      "end_date": time.time(),
                      "measure": "light"}
            r = requests.get(f"{mongoDB_url}/{CompanyName}/avg", params=params)
            r.raise_for_status()
            dict_ = r.json()
            currentLight = dict_["Average"]
        except:
            return None
        else:
            return currentLight

    def callWeatherService(self, CompanyName: str, hour):
        """It gets informations from weather forecast service and extract:
            - cloudCover percentage
            - light
            - sunrise time
            - sunset time

            from the received json file"""

        weatherForecast_url = self.getOtherServiceURL(self.weatherToCall)
        if weatherForecast_url == None or weatherForecast_url == "":
            print("ERROR: Weather Forecast service not found!")
            return None, None, None, None

        try:
            weatherService_data = requests.get(
                f"{weatherForecast_url}/{CompanyName}/lighting")
            weatherService_data.raise_for_status()
            weatherService_data = weatherService_data.json()
        except:
            print("ERROR: Weather Forecast service not available!")
            return None, None, None, None
        else:
            if weatherService_data == {}:
                return None, None, None, None

            light = weatherService_data["hourly"]["Illumination"][hour]

            # Sunrise time extraction and construction:
            sunrise = weatherService_data["daily"]["sunrise"][0]
            sunrise = sunrise.split("T")[1]
            sunriseHour = int(sunrise.split(":")[0])  # retrieves sunrise hour
            # retrieves sunrise minutes
            sunriseMinutes = int(sunrise.split(":")[1])
            sunrise = datetime.time(sunriseHour, sunriseMinutes, 0)

            # Sunset time extraction and construction:
            sunset = weatherService_data["daily"]["sunset"][0]
            sunset = sunset.split("T")[1]
            sunsetHour = int(sunset.split(":")[0])  # retrieves sunset hour
            # retrieves sunset minutes
            sunsetMinutes = int(sunset.split(":")[1])
            sunset = datetime.time(sunsetHour, sunsetMinutes, 0)

            cloudCover = weatherService_data["hourly"]["cloudcover"][hour]

            print("Retrieved weather forecast from Weather Forecast service!")
            return [cloudCover, light, sunrise, sunset]


def sigterm_handler(signal, frame):
    """Handler for the SIGTERM signal."""
    global lighting

    lighting.stop()
    print("SmartLighting stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open("SmartLightingSettings.json", 'r'))
    except FileNotFoundError:
        print("ERROR: files not found")
    else:
        controlTimeInterval = settings["controlTimeInterval"]
        lighting = SmartLighting(settings, controlTimeInterval)

        while True:
            lighting.control()
            time.sleep(controlTimeInterval)
