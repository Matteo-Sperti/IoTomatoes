import paho.mqtt.client as mqtt
import cherrypy
import requests
import time
import json
from statistics import mean
from socket import gethostname, gethostbyname
import sys

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint

ServiceToCall="WeatherForecast" #Global variable: it contains the name of the service that Smart Irrigation must search in the catalog thorugh a get request

class SmartIrrigation(GenericEndpoint):

    def __init__(self, settings : dict):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        super().__init__(settings, isService=True)

        self.commandMessage={
            "bn":"",
            "field":"",
            "actuator":"pump",
            "command":None,
            "timestamp":""
            }

    def notify(self,topic,message):
        """Riceives measures from a specific topic and temporary store them in a
         json file for processing"""
        self.payload=json.loads(message.payload)
        # print(self.payload)
    
        companyName=self.payload["companyName"]
        fieldID=self.payload["field"]
        name=self.payload["e"]["name"]
        measure=self.payload["e"]["value"] #extract the measure vale from MQTT message

        try:
            with open("plantInformation.json") as outfile:
                information=json.load(outfile)
        except FileNotFoundError:
            print("WARNING: file opening error. The file doesn't exist")
        
        if companyName in information["company"]:
            position=information["company"].index(companyName)

            information["companyList"][position]["fields"][fieldID-1]["lastMeasures"][name]["values"].append(measure) #insert the measure value in the json file
            information["companyList"][position]["fields"][fieldID-1]["lastMeasures"][name]["lastUpdate"]=time.time() #update the lastUpdate value in the json file
        
        try:
            with open("plantInformation.json","w") as outfile:
                json.dump(information, outfile, indent=4)
        except FileNotFoundError:
            print("WARNING: file opening error. The file doesn't exist")
        

    def control(self):
        """Extracts measures from the json file, compute the mean value of each type of measure
        and perform the control law"""

        try:
            with open("plantInformation.json") as outfile:
                information=json.load(outfile)          #extract all the information from the json
        except FileNotFoundError:
            print("WARNING: file opening error. The file doesn't exist")

        for company in information["companyList"]:
            companyName=company["companyName"]
            positionCompany=information["company"].index(companyName)   #indicates position index of the single company inside the list of all companies
            print(f"company={positionCompany}")

            for field in company["fields"]:
                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                plant=field["plantType"]
                print(f"campo={fieldID}")
                minTemperature=field["temperatureLimit"]["min"]      #extract the ideal min value of temperature for the given plant from the json file
                maxTemperature=field["temperatureLimit"]["max"]      #extract the ideal max value of temperature from the given plant json file
                minSoilMoisture=field["soilMoistureLimit"]["min"]    #extract the ideal min value of soil moisture for the given plant from the json file 
                maxSoilMoisture=field["soilMoistureLimit"]["max"]    #extract the ideal max value of soil moisture for the given plant from the json file
                precipitationLimit=field["precipitationLimit"]["max"]   #extract the ideal max value of total precipitations for the given plant from the json file
                try:
                    meanTemperature=mean(field["lastMeasures"]["temperature"]["values"])    #compute the mean value of received temperature measures
                    meanSoilMoisture=mean(field["lastMeasures"]["soilMoisture"]["values"])  #compute the mean value of received soil Moisture measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
            

                #CONTROL ALGORITHM:

                dailyPrecipitationSum=self.getPrecipitationSum()
                ############
                #topicList=self.getTopics(company["companyName"],fieldID, ? ) #da aggiungere il systemToken
                ############

                if (meanTemperature<=maxTemperature and meanTemperature>=minTemperature)and(meanSoilMoisture<=maxSoilMoisture and meanSoilMoisture>=minSoilMoisture)and(dailyPrecipitationSum<=precipitationLimit):
                    print(f"""
                    Average temperature={meanTemperature}
                    Average soil moisture={meanSoilMoisture}
                    Daily precipitation sum={dailyPrecipitationSum}
                    Accendi pompe campo {fieldID} ({plant}) di {companyName}""") #per ora il comando è una semplice print
                    
                    #### INVIO COMANDO A OGNI TOPIC DI CIASCUN ATTUATORE NEL CAMPO ####
                    #message=self.commandMessage
                    #message["command"]="ON"
                    #message["timestamp"]=time.time()

                    #for singleTopic in topicList:
                        #self.myPublish(self._baseTopic+singleTopic,message) 
                else:
                    print(f"""
                    Average temperature={meanTemperature}
                    Average soil moisture={meanSoilMoisture}
                    Daily precipitation sum={dailyPrecipitationSum}
                    Spegni pompe campo {fieldID} ({plant}) di {companyName}""") #per ora il comando è una semplice print
                    
                    #### INVIO COMANDO A OGNI TOPIC DI CIASCUN ATTUATORE NEL CAMPO####
                    #message=self.commandMessage
                    #message["command"]="OFF"
                    #message["timestamp"]=time.time()
                    #for singleTopic in topicList:
                        #self.myPublish(self._baseTopic+singleTopic,message) 
                    
                    
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["temperature"]["values"][0:-1] #delete all but one of the used temperature measures
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["soilMoisture"]["values"][0:-1] #delete all but one of the used soil moisture measures

                try:
                    with open("plantInformation.json","w") as outfile:
                        json.dump(information, outfile, indent=4)       #update the json file
                except FileNotFoundError:
                    print("WARNING: file opening error. The file doesn't exist")



    def getPrecipitationSum(self):
        """It gets precipitations informations from weather forecast service and extract 
        the daily precipitation sum from the json file received """

        #RICAVA LE INFORMAZIONI SUL WEATHER FORECAST SERVICE:
        # try:
        #     weatherServiceInfo=requests.get(self.ServiceCatalog_url+"/search/serviceName",params={"serviceName":ServiceToCall})
        #     ## serviceToCall è la variabile globale definita all'inizio dello script che contiene il nome del weather forecast service
        #     weatherServiceInfo.raise_for_status()
        # except requests.exceptions.HTTPError as err:
        #     print(f"{err.response.status_code} : {err.response.reason}")
        #     time.sleep(1)
        # else:  
            #-ESTRAE L'URL DEL WEATHER FORECAST SERVICE:
            # weatherForecast_url=weatherServiceInfo["serviceDetails"][0]["serviceIP"].... 
            # non so se sia giusto il tipo di json che si ottiene eseguendo la ricerca tramite search (ho preso in considerazione
            # la struttura del dizionario relativo al generico servizio scritto sul file del drive )

            #-ESEGUE LA GET AL WEATHER FORECAST SERVICE (da verificare come implementa Luca la gestione della chiamata):
            # try:
            #     weatherService_data=requests.get(weatherForecast_url+"/Irrigation")
            #     weatherService_data.raise_for_status()
            # except requests.exceptions.HTTPError as err:
            #     print(f"{err.response.status_code} : {err.response.reason}")
            #     time.sleep(1)
            # else:
                    #daily_precipitation_sum=weatherService_data["daily"]["precipitation_sum"][0]
                    #return daily_precipitation_sum

        weatherService_data=json.load(open("outputWeatherForecast.json")) #per ora i dati sono presi da un file json esempio (TEMPORANEO)
        daily_precipitation_sum=weatherService_data["daily"]["precipitation_sum"][0]
        return daily_precipitation_sum 
        
    


    def getTopics(self,company,field,token):
        """It retrieves information about resource catalog (by means of genericEndpoint.py method) and then performs a 
        get request to obtain topics from a particulur company in a specified field."""

        #####   CHAMATA AL RESOURCE CATALOG PER OTTENERE LA LISTA DI TOPIC  ####
        # try:
        #     topics_json=requests.get(self.resourceCatalog_url+"/get/topic/pump",params={"companyName":company ,"field":field, "systemToken":token})
        #     topics=json.load(topics_json)
        #     return topics
        # except requests.exceptions.HTTPError as err:
        #     print(f"{err.response.status_code} : {err.response.reason}")
        #     time.sleep(1)





#DA INTEGRARE   
    # exposed=True
    # def GET(self, *uri,**params):
    ### PER POTER FORNIRE EVENTUALMENTE INFORMAZIONI AD ALTRI SERVIZI###

#DA INTEGRARE
    #def POST(self):
    ### PER POTER AGGIORNARE IL JSON CON NUOVE PIANTE SECONDO I BISGONI DELL'UTENTE ###



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
