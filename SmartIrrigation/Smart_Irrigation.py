import requests
import time
import datetime
import json
import sys

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericService
from ItemInfo import *
from MyExceptions import *

weatherToCall="WeatherForecast" #Global variable: name of the service that Smart Irrigation must search in the catalog thorugh a get request
mongoToCall="MongoDB" #Global variable: name of the service that provides previous hour and current measures of each field

class SmartIrrigation(GenericService):

    def __init__(self, settings : dict, plantInfo : dict):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        super().__init__(settings)

        self.plantInfo = plantInfo   
        self._message={
            "bn":"",
            "CompanyName":"",
            "fieldNumber":"",
            "e":{
                "n" : "pump",
                "u" : "/",
                "v" : 0,
                "timestamp":""
            }
        }
      
    def control(self):
        """It performs:
        - Call to resource catalog -> to retrieve information about each field for each company
        - Call to MongoDB to retrieve information about last hour measures (currentSoilMoisture) and previoius hour measures 
          (previousSoilMoisture)
        - Call to Weather forecast service to retrieve information about precipitation during the day
        With these information it performs a control strategy with an hysteresis law in order to send the command ON when the 
        soil moisture mesaure decrease and is under a specific low threshold and to send command OFF in the opposite case"""

        companyList = self.getCompaniesList()

        for company in companyList:
            companyName = company["CompanyName"]

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
                    self.sendCommand(companyName, fieldID, actuatorTopicsForField, 0)
                    continue
                    
                currentTime = datetime.datetime.now().time()
                forecast = self.callWeatherService(currentTime.hour)
                if forecast == None:
                    print("No weather forecast available")
                    self.sendCommand(companyName, fieldID, actuatorTopicsForField, 0)
                    continue

                soilMoistureForecast = forecast[0]    #soilMoisture value provided by the weather forecast
                dailyPrecipitationSum = forecast[1]   #sum of the daily precipitations provided by the weather forecast
                
                currentSoilMoisture = round((3*currentSoilMoisture+soilMoistureForecast)/4,2) #integration sensor measure with the weather forecast one
                maxLimitTemp = datetime.time(23,59,0)
                minLimitTemp = datetime.time(20,0,0)  #da cambiare per poter eseguire le prove sul controllo
                
                #CONTROL ALGORITHM:
                #controllo schedulato per la sera dalle 20 alle 24(quindi sappiamo già complessivamente se durante il giorno ha piovuto)
                print(f"Performing control on: Company={companyName} field={fieldID}")
                if currentTime < minLimitTemp or currentTime > maxLimitTemp:
                    print("NO IRRIGATION TIME")
                    print("pumps set to OFF")
                    self.sendCommand(companyName, fieldID, actuatorTopicsForField, 0)
                else:
                    #PRECIPITATIONS CONTROL:
                    if dailyPrecipitationSum > precipitationLimit:    #soil too moist
                        print("IRRIGATION DOES NOT MAKE SENSE")
                        print("pumps set to OFF")
                        self.sendCommand(companyName, fieldID, actuatorTopicsForField, 0)
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

                        self.sendCommand(companyName, fieldID, actuatorTopicsForField, command)
                                    
                            
    def sendCommand(self, companyName : str, fieldID : int, topicList : list, command : int):
        message=self._message.copy()

        print(f"\nActuators topics list= {topicList}\n")
        for singleTopic in topicList:    
            message["bn"] = self._EndpointInfo["serviceName"]
            message["CompanyName"] = companyName
            message["fieldNumber"] = fieldID
            message["e"]["v"] = command
            message["e"]["timestamp"]=time.time()
        
            print(f"message = {message}\n")
            commandTopic = self._baseTopic + str(singleTopic)
            print(f"command Topic={commandTopic}\n\n")
            self.myPublish(commandTopic, json.dumps(message))

    def getTopics(self, company, fieldNumber : int): 
        """Return the list of the subscribed topics for a field in the company"""
        topics = []
        for device in company["devicesList"]:
            if fieldNumber == device["field"] and device["isActuator"]==True:
                if "pump" in device["actuatorType"]:
                    topics.append(subscribedTopics(device))

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
        #IN FUTURO:
        #POSSIBILE FORMA DELLA CHIAMATA AL SERVICE CATALOG PER OTTENERE L'URL DI MONGODB
        # try:
        #     MongoDB_url=requests.get(self.ServiceCatalog_url+"/search/serviceName",params={"serviceName":"mongoToCall"})
        #     #### mongoToCall è una global variable che rappresenta il nome del mongoDB service nel Service catalog
        #     MongoDB_url.raise_for_status()
        # except requests.exceptions.InvalidURL as errURL:
        #     print(f"ERROR: invalid URL for the Service Catalog!\n\n{errURL})
        #     time.sleep(1)
        # except requests.exceptions.HTTPError as errHTTP:
        #     print(f"ERROR: something went wrong with the Service Catalog!\n\n{errHTTP}")
        #     time.sleep(1)
        # except requests.exceptions.ConnectionError:
        #     print("503: Connection error. Service Catalog unavailable")
        #     time.sleep(1)
        # else:
        #     try:
        #         r=requests.get("MongoDB_url/...media?companyname=<companyName>&fieldID=<ID>&hour=1...") ESPRIMERE BENE L'URL E I PARAMETRI IN RELAZIONE A COME COSTRUISCE IL SERVIZIO LUCA
        #         r.raise_for_status()
        #     except requests.exceptions.InvalidURL as errURL:
        #         print(f"ERROR: invalid URL for MongoDB service!\n\n{errURL}")
        #         time.sleep(1)
        #     except requests.exceptions.HTTPError as errHTTP:
        #         print(f"ERROR: something went wrong with MongoDB service!\n\n{errHTTP}")
        #         time.sleep(1)
        #     except requests.exceptions.ConnectionError:
        #         print("503: Connection error. MongoDB service unavailable")
        #         time.sleep(1)
        #     else:
        #           ####RESTO DEL CODICE####

        #PER ORA I DATI(VALORE MEDIA ORA PRECEDENTE E VALORE MEDIA CORRENTE) VENGONO OTTENUTI DA UNA SORTA DI SIMULATORE MONGODB:
        try:
            r=requests.get("http://127.0.0.1:8080/increasing") 
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
            from the received json file"""
        ####MODIFICA: RICAVARE I DATI DAL WEATHER FORECAST ATTRAVERSO LA CHIAMATA AL SERVICE CATALOG QUI SOTTO COMMENTATA:
        # try:
        #     weatherServiceInfo=requests.get(self.ServiceCatalog_url+"/search/serviceName",params={"serviceName":weatherToCall})
        #     ## weatherToCall è la variabile globale definita all'inizio dello script che contiene il nome del weather forecast service
        #     weatherServiceInfo.raise_for_status()

        # except requests.exceptions.InvalidURL as errURL:
        #     print(f"ERROR: invalid URL for the Service Catalog!\n\n{errURL})
        #     time.sleep(1)
        # except requests.exceptions.HTTPError as errHTTP:
        #     print(f"ERROR: something went wrong with the Service Catalog!\n\n{errHTTP}")
        #     time.sleep(1)
        # except requests.exceptions.ConnectionError:
        #     print("503: Connection error. Service Catalog unavailable")
        #     time.sleep(1)

        # else:
        #-ESTRAE L'URL DEL WEATHER FORECAST SERVICE DALLE INFORMAZIONI RICEVUTE DAL CATALOG:
        #     weatherForecast_url=weatherServiceInfo["serviceDetails"][0]["serviceIP"].... 
        #     non so se sia giusto il tipo di json che si ottiene eseguendo la ricerca tramite search (ho preso in considerazione
        #     la struttura del dizionario relativo al generico servizio scritto sul file del drive )
        #
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
        return [soil_moisture_forecast,daily_precipitation_sum]               
                     

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
        except KeyboardInterrupt:
            irrigation.stop()
            print("SmartIrrigation stopped")
