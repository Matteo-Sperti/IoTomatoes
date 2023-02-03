import requests
import time
import datetime
import json

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.ItemInfo import subscribedTopics

class SmartIrrigation(BaseService):

    def __init__(self, settings : dict, plantInfo : dict):
        """It initializes the service with the settings and the plantInfo
        
        Arguments:\n
        `settings (dict)`: the settings of the service\n
        `plantInfo (dict)`: dictionary with the plants threshold values\n
        """
        super().__init__(settings)

        if "WeatherForecast_ServiceName" in settings:
            self.weatherToCall = settings["WeatherForecast_ServiceName"]

        if "MongoDB_ServiceName" in settings:
            self.mongoToCall = settings["MongoDB_ServiceName"]

        self.plantInfo = plantInfo   
        self._message={
            "bn":"",
            "cn":"",
            "field":"",
            "e":[{
                "n" : "pump",
                "u" : "/",
                "v" : 0,
                "t":""
            }]
        }
      
    def control(self):
        """It performs:
        - Call to resource catalog -> to retrieve information about each field for each company
        - Call to MongoDB to retrieve information about last hour measures (currentSoilMoisture) 
            and previoius hour measures (previousSoilMoisture)
        - Call to Weather forecast service to retrieve information about precipitation during the day
        With these information it performs a control strategy with an hysteresis law in order to send 
        the command ON when the soil moisture mesaure decrease and is under a specific low threshold 
        and to send command OFF in the opposite case"""

        companyList = self.getCompaniesList()

        for company in companyList:
            CompanyName = company["CompanyName"]

            for field in company["fieldsList"]:
                fieldID = field ["fieldNumber"]
                plant = field["plant"]

                #EXTRACT ALL THE ACTUATOR TOPICS FOR THE SPECIFIC FIELD
                actuatorTopicsForField = self.getTopics(company, fieldID)

                if len(actuatorTopicsForField) == 0:
                    print("No actuator topics for the field ", fieldID)
                    continue
                
                minSoilMoisture, maxSoilMoisture, precipitationLimit = self.getPlantLimit(plant)
            
                previousSoilMoisture, currentSoilMoisture = self.getMongoDBdata()
                if previousSoilMoisture == None or currentSoilMoisture == None:
                    print("No previous or current soil moisture measure")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    continue
                    
                currentTime = datetime.datetime.now().time()
                soilMoistureForecast, dailyPrecipitationSum = self.callWeatherService(currentTime.hour)
                if soilMoistureForecast == None or dailyPrecipitationSum == None:
                    print("No weather forecast available")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    continue
                
                #integration sensor measure with the weather forecast one
                currentSoilMoisture = round((3*currentSoilMoisture+soilMoistureForecast)/4,2) 
                maxLimitTemp = datetime.time(23,59,0)
                minLimitTemp = datetime.time(20,0,0)  #da cambiare per poter eseguire le prove sul controllo
                
                #CONTROL ALGORITHM:
                #controllo schedulato per la sera dalle 20 alle 24(quindi sappiamo già complessivamente se durante il giorno ha piovuto)
                print(f"Performing control on: Company={CompanyName} field={fieldID}")
                if currentTime < minLimitTemp or currentTime > maxLimitTemp:
                    print("NO IRRIGATION TIME")
                    print("pumps set to OFF")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                else:
                    #PRECIPITATIONS CONTROL:
                    if dailyPrecipitationSum > precipitationLimit:    #soil too moist
                        print("IRRIGATION DOES NOT MAKE SENSE")
                        print("pumps set to OFF")
                        self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    else:
                        print("IRRIGATION MAKE SENSE")
                        command = 0
                        # HYSTERESIS CONTROL LAW (SOILMOISTURE):
                        # After the precipitations control, we assume that soilMoisture increasing is related
                        # only to our irrigation and not also to possible external phenomena

                        print(f"OFF threshold={maxSoilMoisture}")
                        print(f"ON threshold={minSoilMoisture}")
                        print(f"current value soil moisture={currentSoilMoisture}")
                        print(f"previous value soil moisture={previousSoilMoisture}")
                        
                        if currentSoilMoisture > previousSoilMoisture:
                            print("soilMoisture is increasing")
                            if currentSoilMoisture >= maxSoilMoisture:
                                print(f"""current soil moisture over/on the OFF limit: {currentSoilMoisture}>={maxSoilMoisture}""")
                                print("pumps set to OFF")
                                command = 0
                                
                            else:
                                print(f"""current soil moisture under the OFF limit: {currentSoilMoisture}<{maxSoilMoisture}""")
                                print("pumps set to ON")
                                command = 1
                                
                        elif currentSoilMoisture<previousSoilMoisture:
                            print(f"soilMoisture is decreasing")
                            if currentSoilMoisture <= minSoilMoisture:
                                print(f"""current soil moisture under/on the ON limit: {currentSoilMoisture}<={minSoilMoisture}""")
                                print("pumps set to ON")
                                command = 1
                                
                            else:
                                print(f"""current soil moisture over the ON limit: {currentSoilMoisture}>{minSoilMoisture}""")
                                print("pumps set to OFF")
                                command = 0
                                
                        else:
                            print("costant soil moisture")
                            if currentSoilMoisture > maxSoilMoisture:
                                print("pumps set to OFF")
                                command = 0
                                
                            elif currentSoilMoisture < minSoilMoisture:
                                print("pumps set to ON")
                                command = 1

                        self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, command)
                                    
                            
    def sendCommand(self, CompanyName : str, fieldID : int, topicList : list, command : int):
        message=self._message.copy()

        print(f"\nActuators topics list= {topicList}\n")
        for singleTopic in topicList:    
            message["bn"] = self._EndpointInfo["serviceName"]
            message["cn"] = CompanyName
            message["field"] = fieldID
            message["e"][-1]["v"] = command
            message["e"][-1]["t"]=time.time()
        
            print(f"message = {message}\n")
            commandTopic = str(singleTopic)
            print(f"command Topic={commandTopic}\n\n")
            self._MQTTClient.myPublish(commandTopic, message)

    def getTopics(self, company, fieldNumber : int): 
        """Return the list of the subscribed topics for a field in the company"""
        topics = []
        for device in company["devicesList"]:
            if fieldNumber == device["field"] and device["isActuator"]==True:
                if "pump" in device["actuatorType"]:
                    topics += subscribedTopics(device)

        return topics

    def getPlantLimit(self, plant : str) :
        #Check if the crop is in our json file:
        if plant in list(self.plantInfo.keys()):
            limits=self.plantInfo[plant]
            minSoilMoisture=limits["soilMoistureLimit"]["min"]    #extract the ideal min value of soil moisture for the given plant from the json file 
            maxSoilMoisture=limits["soilMoistureLimit"]["max"]    #extract the ideal max value of soil moisture for the given plant from the json file
            precipitationLimit=limits["precipitationLimit"]["max"]
        else:
            print("No crop with the specified name. \nDefault limits will be used") 
            limits=self.plantInfo["default"]
            minSoilMoisture=limits["soilMoistureLimit"]["min"]    
            maxSoilMoisture=limits["soilMoistureLimit"]["max"]  
            precipitationLimit=limits["precipitationLimit"]["max"] 

        return minSoilMoisture, maxSoilMoisture, precipitationLimit

    def getMongoDBdata(self):
        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)

        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None, None

        #ESEGUE LA GET AL MONGODB SERVICE (da verificare)
        try:
            r=requests.get("http://127.0.0.1:8090/increasing") 
            r.raise_for_status()
            rValues=list((r.json()).values())
            previousSoilMoisture=float(rValues[0])
            currentSoilMoisture=float(rValues[1])
        except:
            return None, None
        else:
            return previousSoilMoisture, currentSoilMoisture

    def callWeatherService(self,hour):
        """It gets precipitations informations from weather forecast service and extract:
            - daily precipitation sum
            - soil moisture forecast
            from the received json file
            """
        weatherForecast_url = self.getOtherServiceURL(self.weatherToCall)
        if weatherForecast_url == None or weatherForecast_url == "":
            print("ERROR: Weather Forecast service not found!")
            return None, None

        #-ESEGUE LA GET AL WEATHER FORECAST SERVICE (da verificare come implementa Luca la gestione della chiamata):
        #     try:
        #         weatherService_data=requests.get(weatherForecast_url+"/Irrigation")
        #         weatherService_data.raise_for_status()
        #     except requests.exceptions.InvalidURL as errURL:
        #         print(f"ERROR: invalid URL for Weather Forecast service!\n\n{errURL})
        #         time.sleep(1)
        #     except requests.exceptions.HTTPError as errHTTP:
        #         print(f"ERROR: something went wrong with Weather Forecast service!\n\n{errHTTP}")
        #         time.sleep(1)
        #     except requests.exceptions.ConnectionError:
        #         print("503: Connection error. Weather Forecast service unavailable")
        #         time.sleep(1)

        #     else:
        #         weatherService_data=weatherService_data.json()
        #         daily_precipitation_sum=weatherService_data["daily"]["precipitation_sum"][0]
        #         soil_moisture_forecast=weatherService_data["hourly"]["soil_moisture_3_9cm"][hour]
        #         return [soil_moisture_forecast,daily_precipitation_sum]
        
        #PER ORA I DATI SONO PRESI SEMPLICEMENTE DA UN FILE:
        weatherService_r=json.load(open("outputWeatherForecast.json"))
        daily_precipitation_sum=weatherService_r["daily"]["precipitation_sum"][0]
        soil_moisture_forecast=weatherService_r["hourly"]["soil_moisture_3_9cm"][hour]
        return soil_moisture_forecast,daily_precipitation_sum              
                     

if __name__=="__main__":
    try:
        settings = json.load(open("SmartIrrigationSettings.json", 'r'))
        plantDatabase = json.load(open("plantThreshold.json", 'r'))
    except FileNotFoundError:
        print("ERROR: files not found")
    else:
        irrigation = SmartIrrigation(settings, plantDatabase)

        controlTimeInterval = settings["controlTimeInterval"]
        try:
            while True:
                irrigation.control()
                time.sleep(controlTimeInterval)
        except KeyboardInterrupt or SystemExit:
            irrigation.stop()
            print("SmartIrrigation stopped")
