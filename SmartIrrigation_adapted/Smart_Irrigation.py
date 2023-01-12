import paho.mqtt.client as mqtt
import requests
import cherrypy
import time
import datetime
import json
from socket import gethostname, gethostbyname
import sys

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint

weatherToCall="WeatherForecast" #Global variable: name of the service that Smart Irrigation must search in the catalog thorugh a get request
mongoToCall="MongoDB" #Global variable: name of the service that provides previous hour and current measures of each field
class SmartIrrigation(GenericEndpoint):

    def __init__(self, settings : dict):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        super().__init__(settings, isService=True)

        self.message={
            "bn":"",
            "e":{
                "deviceID":"",
                "field":"",
                "command":"",
                "timestamp":""
            }
        }
    ####### ORMAI E' SOLO PUBLISHER PER CUI NON RICEVE PIU' LE MISURE DAI SENSORI 
    # def notify(self,topic,message):
    #     """Riceives measures from a specific topic and temporary store them in a
    #      json file for processing"""
    #     self.payload=json.loads(message.payload)
    #     # print(self.payload)
    
    #     companyName=self.payload["companyName"]
    #     fieldID=self.payload["field"]
    #     name=self.payload["e"]["name"]
    #     measure=self.payload["e"]["value"] #extract the measure vale from MQTT message

    #     try:
    #         with open("plantInformation.json") as outfile:
    #             information=json.load(outfile)
    #     except FileNotFoundError:
    #         print("WARNING: file opening error. The file doesn't exist")
        
    #     if companyName in information["company"]:
    #         position=information["company"].index(companyName)

    #         information["companyList"][position]["fields"][fieldID-1]["lastMeasures"][name]["values"].append(measure) #insert the measure value in the json file
    #         information["companyList"][position]["fields"][fieldID-1]["lastMeasures"][name]["lastUpdate"]=time.time() #update the lastUpdate value in the json file
        
    #     try:
    #         with open("plantInformation.json","w") as outfile:
    #             json.dump(information, outfile, indent=4)
    #     except FileNotFoundError:
    #         print("WARNING: file opening error. The file doesn't exist")


    def control(self):
        """It performs:
        - Call to resource catalog -> to retrieve information about each field for each company
        - Call to MongoDB to retrieve information about last hour measures (currentSoilMoisture) and previoius hour measures 
          (previousSoilMoisture)
        - Call to Weather forecast service to retrieve information about precipitation during the day
        With these information it performs a control strategy with an hysteresis law in order to send the command ON when the 
        soil moisture mesaure decrease and is under a specific low threshold and to send command OFF in the opposite case"""

        message=self.message
        #### IMPLEMENTARE CHIAMATA AL RESOURCE CATALOG PER RICEVERE LE INFORMAZIONI
        plant="potatoes"  #da aggiungere nel resource catalog 
        message["e"]["command"]=""  #per ogni field il messaggio dovrà essere vuoto

        request=json.load(open("ResourceCatalog.json"))
        companyList=request["companiesList"]

        ##### MODIFICARE IL CICLO IN RELAZIONE A COME VERRANNO INSERITI I FIELD ALL'INTERNO DEL RESOURCE CATALOG.
        ##### PER ORA I FIELD SONO STATI INSERITI ALL'INTERNO DEL FILE USATO COME RESOURCE CATALOG FITTIZIO
        for company in companyList:
            IDcompany=company["ID"]                 #probabilmente necessario(?)... SE NO, CANCELLARE
            companyName=company["CompanyName"]
            companyToken=company["CompanyToken"]    #probabilmente necessario(?)... SE NO, CANCELLARE

            for field in company["fieldsList"]:
                actuatorsForField=[]
                fieldID=field["fieldID"]

                #PER ORA, GLI ID DI OGNI ATTUATORE VENGONO OTTENUTI ESTRAPOLANDOLI (DECIDERE SE LASCIARLO COSI O USARE IL METODO AD HOC DI MATTEO)
                for device in company["devicesList"]:
                    if fieldID == device["field"] and device["isActuator"]==True and device["actuatorType"][0]=="pump":
                        actuatorsForField.append(device["ID"])
                print(actuatorsForField)    
                
                try:
                    with open("plantThreshold.json") as outfile:
                        plantInfo=json.load(outfile)          
                except FileNotFoundError:
                    print("ERROR: file not found")
        

            #Check if the crop is in our json file:
            if plant in list(plantInfo.keys()):
                limits=plantInfo[plant]
                minSoilMoisture=limits["soilMoistureLimit"]["min"]    #extract the ideal min value of soil moisture for the given plant from the json file 
                maxSoilMoisture=limits["soilMoistureLimit"]["max"]    #extract the ideal max value of soil moisture for the given plant from the json file
                precipitationLimit=limits["precipitationLimit"]["max"]
            else:
                print("No crop with the specified name. \nDefault limits will be used") 
                limits=plantInfo["default"]
                minSoilMoisture=limits["soilMoistureLimit"]["min"]    
                maxSoilMoisture=limits["soilMoistureLimit"]["max"]  
                precipitationLimit=limits["precipitationLimit"]["max"]  
        
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
            except requests.exceptions.InvalidURL as errURL:
                print(f"ERROR: invalid URL for MongoDB service!\n\n{errURL}")
                time.sleep(1)
            except requests.exceptions.HTTPError as errHTTP:
                print(f"ERROR: something went wrong with MongoDB service!\n\n{errHTTP}")
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                print("503: Connection error. MongoDB service unavailable")
                time.sleep(1)
                
            else:
                rValues=list((r.json()).values())
                previousSoilMoisture=float(rValues[0])
                currentSoilMoisture=float(rValues[1])
                
                currentTime=datetime.datetime.now().time()
                forecast=self.callWeatherService(currentTime.hour)
                soilMoistureForecast=forecast[0]    #soilMoisture value provided by the weather forecast
                dailyPrecipitationSum=forecast[1]   #sum of the daily precipitations provided by the weather forecast
                
                currentSoilMoisture=round((3*currentSoilMoisture+soilMoistureForecast)/4,2) #integration sensor measure with the weather forecast one
                maxLimitTemp=datetime.time(23,59,0)
                minLimitTemp=datetime.time(20,0,0)  #da cambiare per poter eseguire le prove sul controllo
                
                #CONTROL ALGORITHM:
                #controllo schedulato per la sera dalle 20 alle 24(quindi sappiamo già complessivamente se durante il giorno ha piovuto)
        
                if currentTime>=minLimitTemp and currentTime<=maxLimitTemp:
                    print(f"Performing control on: Company={companyName} field={fieldID}")
                    #PRECIPITATIONS CONTROL:
                    if dailyPrecipitationSum>precipitationLimit:    #soil too moist
                        print("IRRIGATION DOES NOT MAKE SENSE")
                        print("pumps set to OFF")
                        message["e"]["command"]="OFF"
                    else:
                        print("IRRIGATION MAKE SENSE")
                        
                        # HYSTERESIS CONTROL LAW (SOILMOISTURE):
                        # After the precipitations control, we assume that soilMoisture increasing is related
                        # only to our irrigation and not also to possible external phenomena

                        print(f"OFF threshold={maxSoilMoisture}")
                        print(f"ON threshold={minSoilMoisture}")
                        print(f"current value soil moisture={currentSoilMoisture}")
                        print(f"previous value soil moisture={previousSoilMoisture}")
                        
                        if currentSoilMoisture>previousSoilMoisture:
                            print("soilMoisture is increasing")
                            if currentSoilMoisture>=maxSoilMoisture:
                                print(f"""current soil moisture over/on the OFF limit: {currentSoilMoisture}>={maxSoilMoisture}""")
                                print("pumps set to OFF")
                                message["e"]["command"]="OFF"
                                
                            else:
                                print(f"""current soil moisture under the OFF limit: {currentSoilMoisture}<{maxSoilMoisture}""")
                                print("pumps set to ON")
                                message["e"]["command"]="ON"
                                
                        elif currentSoilMoisture<previousSoilMoisture:
                            print(f"soilMoisture is decreasing")
                            if currentSoilMoisture<=minSoilMoisture:
                                print(f"""current soil moisture under/on the ON limit: {currentSoilMoisture}<={minSoilMoisture}""")
                                print("pumps set to ON")
                                message["e"]["command"]="ON"
                                
                            else:
                                print(f"""current soil moisture over the ON limit: {currentSoilMoisture}>{minSoilMoisture}""")
                                print("pumps set to OFF")
                                message["e"]["command"]="OFF"
                                
                        else:
                            print("costant soil moisture")
                            if currentSoilMoisture>maxSoilMoisture:
                                print("pumps set to OFF")
                                message["e"]["command"]="OFF"
                                
                            elif currentSoilMoisture<minSoilMoisture:
                                print("pumps set to ON")
                                message["e"]["command"]="ON"
                                    
                            
                else:
                    print("NO IRRIGATION TIME")
                    print("pumps set to OFF")
                    message["e"]["command"]="OFF"

                for actuatorID in actuatorsForField:    
                    message["bn"]=companyName
                    message["e"]["deviceID"]=actuatorID
                    message["e"]["field"]=fieldID
                    message["e"]["timeStamp"]=time.time()
                
                    print(f"message= {message}\n")
                    commandTopic=self._baseTopic+str(companyName)+"/"+str(fieldID)+"/"+str(actuatorID)+"/pump"
                    print(f"command Topic={commandTopic}\n\n")
                    self.myPublish(commandTopic,json.dumps(message))
  
                
                
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
        #         weatherService_r=weatherService_data.json()
        
        #PER ORA I DATI SONO PRESI SEMPLICEMENTE DA UN FILE:
        weatherService_r=json.load(open("outputWeatherForecast.json"))
        daily_precipitation_sum=weatherService_r["daily"]["precipitation_sum"][0]
        soil_moisture_forecast=weatherService_r["hourly"]["soil_moisture_3_9cm"][hour]
        return [soil_moisture_forecast,daily_precipitation_sum]               
                     
        
    

#SE ADOPERIAMO L'ESTRAZIONE DEGLI ACTUATOR ID DIRETTAMENTE DA QUANTO OTTENUTO DAL RESOURCE CATALOG QUESTO METODO E' DA CANCELLARE
    def getTopics(self,company,field,token):
        """It retrieves information about resource catalog (by means of genericEndpoint.py method) and then performs a 
        get request to obtain topics from a particulur company in a specified field."""

        #####   CHAMATA AL RESOURCE CATALOG PER OTTENERE LA LISTA DI TOPIC  ####
        # try:
        #     topics_json=requests.get(self.resourceCatalog_url+"/get/topic/pump",params={"companyName":company ,"field":field, "systemToken":token})
        #     topics=json.load(topics_json)
        #     return topics
        # except requests.exceptions.InvalidURL as errURL:
        #     print(f"ERROR: invalid URL for the Resource Catalog!\n\n{errURL}")
        #     time.sleep(1)
        # except requests.exceptions.HTTPError as errHTTP:
        #     print(f"ERROR: something went wrong with Resource catalog!\n\n{errHTTP}")
        #     time.sleep(1)
        # except requests.exceptions.ConnectionError:
        #     print("503: Connection error. Resource catalog unavailable")
        #     time.sleep(1)




if __name__=="__main__":
    settings = json.load(open("SmartIrrigationSettings.json"))

    ip_address = gethostbyname(gethostname())
    port = settings["IPport"]
    settings["IPaddress"] = ip_address

    conf = {
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }

    irrigation=SmartIrrigation(settings)
    irrigation.start()

    ####visto che ormai il servizio è solo un publisher MQTT ha senso definire le caratteristiche di un servizio REST?
    cherrypy.tree.mount(irrigation, "/", conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    try:
        while True:
            irrigation.control()
            time.sleep(30)
    except KeyboardInterrupt:
        irrigation.stop()
        cherrypy.engine.block()
        print("SmartIrrigation stopped")
