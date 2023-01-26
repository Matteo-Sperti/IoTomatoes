import requests
import time
import datetime
import json

from iotomatoes_supportpackage.GenericEndpoint import GenericService
from iotomatoes_supportpackage.ItemInfo import subscribedTopics

class SmartLighting(GenericService):

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
        self._message = {
            "bn": self._EndpointInfo["serviceName"],
            "cn":"",
            "field":"",
            "e": [{
                "n" : "led",
                "u" : "/",
                "v" : 0,
                "t":""
            }]
        }


    def control(self):
        """It performs:
        - Call to resource catalog -> to retrieve information about each field for each company
        - Call to MongoDB to retrieve information about last hour measures (currentLigh) and previous hour measures 
          (previousLight)
        - Call to Weather forecast service to retrieve information about current cloudcover percentage, light, 
        sunrise hour and sunset hour. 
        With these information it integrates the forecast light with sensor measures and performs a simple control 
        strategy to check if the light is under a fixed threshold"""

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
                
                minLight, maxLight = self.getPlantLimit(plant)
                if minLight == None or maxLight == None:
                    print("No previous or current light measure")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    continue 

                currentLight = self.getMongoDBdata()
                if currentLight == None:
                    print("No previous or current soil moisture measure")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    continue   

                currentTime = datetime.datetime.now().time()
                cloudCover, lightForecast, Sunrise, Sunset = self.callWeatherService(currentTime.hour)
                if cloudCover == None or lightForecast == None or Sunrise == None or Sunset == None:
                    print("No weather forecast available")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    continue
                
                #integration sensor measures with the weather forecast one
                currentLight=round((3*currentLight+lightForecast)/4,2) 

                #CONTROL ALGORITHM:
                #controllo schedulato dall'inizio dell'alba al tramonto (LA NOTTE NO, COSI SI LASCIA UN
                # CICLO LUCE/BUIO ALLE PIANTE PER LA FOTOSINTESI)                
                print(f"Performing control on: Company={CompanyName} field={fieldID}")
                if currentTime < Sunrise or currentTime > Sunset:
                    print("IT'S NIGHT, NO LIGHTING TIME")
                    print("light set to OFF")
                    self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                else:
                    #CLOUDCOVER CONTROL
                    if cloudCover < 60:  
                        print("LIGHTING DOES NOT MAKE SENSE")
                        print("light set to OFF")
                        self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, 0)
                    else:    
                        command = 0
                        print("LIGHTING MAKE SENSE")
                        print(f"ON/OFF threshold={minLight}")
                        print(f"current value light={currentLight}")
                        
                        if currentLight<=minLight:
                            print("light set to ON")
                            command = 1
                        
                        else:
                            print("light set to OFF")
                            command = 1

                        self.sendCommand(CompanyName, fieldID, actuatorTopicsForField, command)


    def sendCommand(self, CompanyName : str, fieldID : int, topicList : list, command : int):
        message=self._message.copy()

        print(f"\nActuators topics list= {topicList}\n")
        for singleTopic in topicList:    
            message["cn"] = CompanyName
            message["field"] = fieldID
            message["e"][-1]["v"] = command
            message["e"][-1]["t"]=time.time()
        
            print(f"message = {message}")
            commandTopic = str(singleTopic)
            print(f"command Topic={commandTopic}\n")
            self.myPublish(commandTopic, message)

    def getTopics(self, company, fieldNumber : int): 
        """Return the list of the subscribed topics for a field in the company"""
        topics = []
        for device in company["devicesList"]:
            if fieldNumber == device["field"] and device["isActuator"]==True:
                if "led" in device["actuatorType"]:
                    topics += subscribedTopics(device)

        return topics

    def getPlantLimit(self, plant : str) :
        #Check if the crop is in our json file:
        if plant in list(self.plantInfo.keys()):
            limits=self.plantInfo[plant]
            minLight=limits["lightLimit"]["min"]    #ideal min value of light for the given plant
            maxLight=limits["lightLimit"]["max"]    #ideal max value of light for the given plant
        else:
            print("No crop with the specified name. \nDefault limits will be used") 
            limits=self.plantInfo["default"]
            minLight=limits["lightLimit"]["min"]
            maxLight=limits["lightLimit"]["max"]  

        return minLight, maxLight            

    def getMongoDBdata(self):
        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)

        if mongoDB_url == None or mongoDB_url == "":
            print("ERROR: MongoDB service not found!")
            return None, None

        ###ESEGUE LA GET AL MONGODB
        try:
            r=requests.get("http://127.0.0.1:8080/decreasing")
            r.raise_for_status()
            rValues=list((r.json()).values())
            currentLight=float(rValues[0])
        except:
            return None,
        else:
            return currentLight        

    def callWeatherService(self,hour):
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

        #
        #-ESEGUE LA GET AL WEATHER FORECAST SERVICE (da verificare come implementa Luca la gestione della chiamata):
        #     try:
        #         weatherService_data=requests.get(weatherForecast_url+"/Lighting")
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
        #         light=weatherService_data["hourly"]["sunLight"][hour]

        #         #Estrazione e costruzione orario alba:
        #         sunrise=weatherService_data["daily"]["sunrise"][0]
        #         sunrise=sunrise.split("T")[1]
        #         sunriseHour=int(sunrise.split(":")[0]) #retrieves sunrise hour
        #         sunriseMinutes=int(sunrise.split(":")[1]) #retrieves sunrise minutes
        #         sunrise=datetime.time(sunriseHour,sunriseMinutes,0) #crea un oggetto "data" con per avere l'ora dell'alba
        
        #         #Estrazione e costruzione orario tramonto:
        #         sunset=weatherService_data["daily"]["sunset"][0]
        #         sunset=sunset.split("T")[1]
        #         sunsetHour=int(sunset.split(":")[0]) #retrieves sunset hour
        #         sunsetMinutes=int(sunset.split(":")[1]) #retrieves sunset minutes
        #         sunset=datetime.time(sunsetHour,sunsetMinutes,0) #crea un oggetto "data" per avere l'ora del tramonto
        
        #         cloudCover=weatherService_data["hourly"]["cloudcover"][hour]
        #         return [cloudCover,light,sunrise,sunset]
        
        #PER ORA I DATI SONO PRESI SEMPLICEMENTE DA UN FILE
        weatherService_r=json.load(open("outputLighting.json"))
        light=weatherService_r["hourly"]["sunLight"][hour]

        #Estrazione e costruzione orario alba:
        sunrise=weatherService_r["daily"]["sunrise"][0]
        sunrise=sunrise.split("T")[1]
        sunriseHour=int(sunrise.split(":")[0]) #retrieves sunrise hour
        sunriseMinutes=int(sunrise.split(":")[1]) #retrieves sunrise minutes
        sunrise=datetime.time(sunriseHour,sunriseMinutes,0) #crea un oggetto "data" con per avere l'ora dell'alba
        
        #Estrazione e costruzione orario tramonto:
        sunset=weatherService_r["daily"]["sunset"][0]
        sunset=sunset.split("T")[1]
        sunsetHour=int(sunset.split(":")[0]) #retrieves sunset hour
        sunsetMinutes=int(sunset.split(":")[1]) #retrieves sunset minutes
        sunset=datetime.time(sunsetHour,sunsetMinutes,0) #crea un oggetto "data" per avere l'ora del tramonto
        
        cloudCover=weatherService_r["hourly"]["cloudcover"][hour]
        return cloudCover,light,sunrise,sunset                      
    
if __name__=="__main__":
    try:
        settings = json.load(open("SmartLightingSettings.json", 'r'))
        plantDatabase = json.load(open("lightThreshold.json", 'r'))
    except FileNotFoundError:
        print("ERROR: files not found")
    else:
        lighting = SmartLighting(settings, plantDatabase)

        controlTimeInterval = settings["controlTimeInterval"]
        try:
            while True:
                lighting.control()
                time.sleep(controlTimeInterval)
        except KeyboardInterrupt or SystemExit:
            lighting.stop()
            print("SmartLighting stopped")