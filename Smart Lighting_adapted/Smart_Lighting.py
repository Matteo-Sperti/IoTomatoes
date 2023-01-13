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

weatherToCall="WeatherForecast" #Global variable: name of the service that Smart Lighting must search in the catalog thorugh a get request
mongoToCall="MongoDB" #Global variable: name of the service that provides previous hour and current measures of each field


class SmartLighting(GenericEndpoint):

    def __init__(self, settings : dict):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        super().__init__(settings, isService=True)

        self.message={
            "bn":"",
            "e":{
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
        - Call to MongoDB to retrieve information about last hour measures (currentLigh) and previous hour measures 
          (previousLight)
        - Call to Weather forecast service to retrieve information about current cloudcover percentage, light, sunrise hour and sunset hour
        With these information it integrates the forecast light with sensor measures and performs a simple control strategy to check if the light is under a fixed threshold"""

        message=self.message
        #### IMPLEMENTARE CHIAMATA AL RESOURCE CATALOG PER RICEVERE LE INFORMAZIONI        
        plant="potatoes"

        request=json.load(open("ResourceCatalog.json"))
        companyList=request["companiesList"]
        
        ##### MODIFICARE IL CICLO IN RELAZIONE A COME VERRANNO INSERITI I FIELD ALL'INTERNO DEL RESOURCE CATALOG.
        ##### PER ORA I FIELD SONO STATI INSERITI ALL'INTERNO DEL FILE USATO COME RESOURCE CATALOG FITTIZIO
        for company in companyList:
            IDcompany=company["ID"]                 #probabilmente necessario(?)... SE NO, CANCELLARE
            companyName=company["CompanyName"]
            companyToken=company["CompanyToken"]    #probabilmente necessario(?)... SE NO, CANCELLARE

            for field in company["fieldsList"]:
                message["e"]["command"]="" #per ogni field il messaggio deve essere vuoto
                actuatorTopicsForField=[]
                fieldID=field["fieldID"]

                for device in company["devicesList"]:
                    if fieldID == device["field"] and device["isActuator"]==True and device["actuatorType"][0]=="led":
                        actuatorTopicsForField.append(device["servicesDetails"][0]["subscribedTopics"][0])
                   
                try:
                    with open("lightThreshold.json") as outfile:
                        lightInfo=json.load(outfile)          
                except FileNotFoundError:
                    print("ERROR: file 'lightThreshold.json' not found")
            
            
                #Check if the crop is in our json file:
                if plant in list(lightInfo.keys()):
                    limits=lightInfo[plant]
                    minLight=limits["lightLimit"]["min"]    #extract the ideal min value of light for the given plant from the json file 
                    maxLight=limits["lightLimit"]["max"]    #extract the ideal max value of light for the given plant from the json file
                else:
                    print("No crop with the specified name. \nDefault limits will be used") 
                    limits=lightInfo["default"]
                    minLight=limits["lightLimit"]["min"]
                    maxLight=limits["lightLimit"]["max"]
                
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
                    r=requests.get("http://127.0.0.1:8080/decreasing") #richiesta al MongoDBSimulator, da sostituire con il vero mongoDB
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
                    previousLight=float(rValues[0])
                    currentLight=float(rValues[1])
                    
                    #currentTime=datetime.datetime.now().time() ###DA USARE UNA VOLTA CHE LE PROVE SONO FINITE
                    currentTime=datetime.time(16,0,0) #per fare le prove(permette di simulare l'ora corrente e porla a un valore voluto, in questo caso le 16)
                    forecast=self.callWeatherService(currentTime.hour)
                    cloudCover=forecast[0]
                    lightForecast=forecast[1]
                    Sunrise=forecast[2]
                    Sunset=forecast[3]
                    
                    currentLight=round((3*currentLight+lightForecast)/4,2) #integration sensor measures with the weather forecast one

                    #CONTROL ALGORITHM:
                    #controllo schedulato dall'inizio dell'alba al tramonto (LA NOTTE NO, COSI SI LASCIA UN
                    # CICLO LUCE/BUIO ALLE PIANTE PER LA FOTOSINTESI)
                    
                    print(f"Performing control on: Company={companyName} field={fieldID}")
                    if currentTime>=Sunrise and currentTime<=Sunset:
                        #CLOUDCOVER CONTROL
                        if cloudCover>=60:  #cosi se temporaneamente passa una nuvola che abbassa troppo il valore di luce non si accendono comunque
                            print("LIGHTING MAKE SENSE")
                            #print(f"OFF threshold={maxLight}")
                            print(f"ON/OFF threshold={minLight}")
                            print(f"current value light={currentLight}")
                            print(f"previous value light={previousLight}")
                            
                            #1) POSSIBILE CONTROL LAW IPOTIZZANDO CHE LE MISURE DEI SENSORI DI LUCE NON VENGANO INFLUENZATE DALLE LUCI ARTIFICIALI: 
                            # if currentLight>previousLight:
                            #     print("light is increasing")
                            #     if currentLight>=maxLight:
                            #         print(f"""current light over/on the OFF limit: {currentLight}>={maxLight}""")
                            #         print("light set to OFF")
                            #         message["e"]["command"]="OFF"
                                    
                            #     else:
                            #         print(f"""current light under the OFF limit: {currentLight}<{maxLight}""")
                            #         print("light set to ON")
                            #         message["e"]["command"]="ON"
                                    

                            # elif currentLight<previousLight:
                            #     print("light is decreasing")
                            #     if currentLight<=minLight:
                            #         print(f"""current light under/on the ON limit: {currentLight}<={minLight}""")
                            #         print("light set to ON")
                            #         message["e"]["command"]="ON"
                                    
                            #     else:
                            #         print(f"current light over the ON limit: {currentLight}>{minLight}""")
                            #         print("light set to OFF")
                            #         message["e"]["command"]="OFF"
                                    
                            # else:
                            #     print("costant light")
                            #     if currentLight>maxLight:
                            #         print("light set to OFF")
                            #         message["e"]["command"]="OFF"
                                    
                            #     elif currentLight<minLight:
                            #         print("light set to ON")
                            #         message["e"]["command"]="ON"
                            #
                            #2) CONTROL LAW MONOSOGLIA:
                            if currentLight<=minLight:
                                print("light set to ON")
                                message["e"]["command"]="ON"
                            
                            else:
                                print("light set to OFF")
                                message["e"]["command"]="OFF"

                        else:
                            print("LIGHTING DOES NOT MAKE SENSE")
                            print("light set to OFF")
                            message["e"]["command"]="OFF"

                    else:
                        print("IT'S NIGHT, NO LIGHTING TIME")
                        print("light set to OFF")
                        message["e"]["command"]="OFF"
                    
                    print(f"\nActuators topics list= {actuatorTopicsForField}\n")
                    for singleTopic in actuatorTopicsForField:
                        message["bn"]=companyName
                        message["e"]["field"]=fieldID
                        message["e"]["timeStamp"]=time.time()
                    
                        print(f"message= {message}")

                        commandTopic=self._baseTopic+str(singleTopic)
                        print(f"command Topic={commandTopic}\n\n")
                        self.myPublish(commandTopic,json.dumps(message))
  
                
                
    def callWeatherService(self,hour):
        """It gets precipitations informations from weather forecast service and extract:
            - daily precipitation sum
            - soil moisture forecast
            from the received json file"""
        ####MODIFICA: RICAVARE I DATI DAL WEATHER FORECAST ATTRAVERSO LA CHIAMATA AL SERVICE CATALOG
        # try:
        ##     weatherServiceInfo=requests.get(self.ServiceCatalog_url+"/search/serviceName",params={"serviceName":weatherToCall})
        #     ## weatherToCall è la variabile globale definita all'inizio dello script che contiene il nome del weather forecast service
        #     weatherServiceInfo.raise_for_status()

        # except requests.exceptions.InvalidURL as errURL:
        #     print(f"ERROR: invalid URL for the Service Catalog!\n\n{errURL})
        #     time.sleep(1)
        # except requests.exceptions.HTTPError as errHTTP:
        #     pprint(f"ERROR: something went wrong with the Service Catalog!\n\n{errHTTP}")
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
        return [cloudCover,light,sunrise,sunset]               
                     
        



if __name__=="__main__":
    try:
        with open("SmartLightingSettings.json") as outfile:
            settings=json.load(outfile)
    except FileNotFoundError:
        print("ERROR: file 'SmartLightingSettings.json' not found")

    ip_address = gethostbyname(gethostname())
    port = settings["IPport"]
    settings["IPaddress"] = ip_address

    conf = {
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }

    lighting=SmartLighting(settings)
    lighting.start()

    ####visto che ormai il servizio è solo un publisher MQTT ha senso definire le caratteristiche di un servizio REST?
    cherrypy.tree.mount(lighting, "/", conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    try:
        while True:
            lighting.control()
            time.sleep(30)
    except KeyboardInterrupt:
        lighting.stop()
        cherrypy.engine.block()
        print("SmartIrrigation stopped")
