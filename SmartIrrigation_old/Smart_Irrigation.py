import paho.mqtt.client as mqtt
import cherrypy
import time
import json
from statistics import mean
import requests


class SmartIrrigation:

    def __init__(self):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""

        self.serviceID="Irrigation"
        self.sensor_topic="IoTomatoes/+/+/+/measure" #IoTomatoes/companyName/field/deviceID/measure
        self.broker="test.mosquitto.org"
        self.port=1883

        
        self.service_mqtt=mqtt.Client(self.serviceID,True)

        #CALLBACK
        self.service_mqtt.on_connect=self.myOnConnect
        self.service_mqtt.on_message=self.myOnMessage

    def start(self):
        """Connects and subscribes the service to the broker"""
        self.service_mqtt.connect(self.broker,self.port)
        self.service_mqtt.loop_start()
        self.service_mqtt.subscribe(self.sensor_topic,2)
    
    def myOnConnect(self,client,userdata,flags,rc):
        """It provides information about Connection result with the broker"""
        dic={
            "0":f"Connection successful to {self.broker}",
            "1":f"Connection to {self.broker} refused - incorrect protocol version",
            "2":f"Connection to {self.broker} refused - invalid client identifier",
            "3":f"Connection to {self.broker} refused - server unavailable",
        }
             
        print(dic[str(rc)])
    
    def myOnMessage(self,client,userdata,message):
        """Riceives measures from a specific topic and temporary store them in a
         json file for processing"""
        self.payload=json.loads(message.payload)
        # print(self.payload)
    
        companyName=self.payload["companyName"]
        fieldID=self.payload["field"]
        name=self.payload["e"]["name"]
        measure=self.payload["e"]["value"] #extract the measure vale from MQTT message

        with open("plantInformation.json") as outfile:
            information=json.load(outfile)
        
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
                precipitationLimit=field["precipitationLimit"]["max"]

                previousMeanTemperature=field["lastMeasures"]["temperature"]["previousValue"]
                previousMeanSoilMoisture=field["lastMeasures"]["soilMoisture"]["previousValue"]
                try:
                    currentTemperature=mean(field["lastMeasures"]["temperature"]["values"])    #compute the mean value of received temperature measures
                    currentSoilMoisture=mean(field["lastMeasures"]["soilMoisture"]["values"])  #compute the mean value of received soil Moisture measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
            

                #CONTROL ALGORITHM:
                dailyPrecipitationSum=self.callWeatherService()



                #TENTATIVO 1) CONTROL LAW CON SOLO SOILMOISTURE
                if dailyPrecipitationSum>precipitationLimit:
                    print("NON HA SENSO IRRIGARE")
                    print("pompe OFF")
                else:
                    print("HA SENSO IRRIGARE")

                    soilMoistureON=minSoilMoisture*1.05
                    soilMoistureOFF=maxSoilMoisture*0.95

                    print(f"limite OFF={soilMoistureOFF}")
                    print(f"limite ON={soilMoistureON}")
                    print(f"current value soil moisture={currentSoilMoisture}")
                    
                    if currentSoilMoisture<minSoilMoisture:
                        print("umidità sotto la soglia minima assoluta, necessario irrigare")
                        print("POMPE ACCESE")
                    elif currentSoilMoisture>maxSoilMoisture:
                        print("umidità oltre la soglia massima assoluta, neccessario non irrigare e lasciare asciugare")
                        print("POMPE SPENTE")
                        #possibile implementazione chiamata al lighting service per accendere le luci, riscaldare le piante e 
                        #e velocizzare la riduzione dell'umidità
                    else:
                        print("siamo all'interno del range ideale per la pianta")
                        if currentSoilMoisture>previousMeanSoilMoisture:
                            print("soilMoisture sta aumentando")
                            if currentSoilMoisture>=soilMoistureOFF:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}>={soilMoistureOFF}""")
                                print("POMPE SPENTE")
                            else:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}<{soilMoistureOFF}""")
                                print("POMPE ACCESE")
                        elif currentSoilMoisture<previousMeanSoilMoisture:
                            print("soilMoisture sta diminuendo")
                            if currentSoilMoisture<=soilMoistureON:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}<={soilMoistureON}""")
                                print("POMPE ACCESE")
                            else:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}>{soilMoistureON}""")
                                print("POMPE SPENTE")
                        else:
                            print("soil moisture costante")

                # if (meanTemperature<=maxTemperature and meanTemperature>=minTemperature)and(meanSoilMoisture<=maxSoilMoisture and meanSoilMoisture>=minSoilMoisture)and(dailyPrecipitationSum<=precipitationLimit):
                #     print(f"""
                #     Average temperature={meanTemperature}
                #     Average soil moisture={meanSoilMoisture}
                #     Daily precipitation sum={dailyPrecipitationSum}
                #     Accendi pompe campo {fieldID} ({plant}) di {companyName}""")
                #         #self.service_mqtt.publish(topic_attuatori) 
                # else:
                #     print(f"""
                #     Average temperature={meanTemperature}
                #     Average soil moisture={meanSoilMoisture}
                #     Daily precipitation sum={dailyPrecipitationSum}
                #     Spegni pompe campo {fieldID} ({plant}) di {companyName}""")
                #     #self.service_mqtt.publish(topic_attuatori)
                    
                #AGGIORNA L'ULTIMO VALORE DI MEDIA OTTENUTO:
                information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["temperature"]["previousValue"]=currentTemperature
                information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["soilMoisture"]["previousValue"]=currentSoilMoisture

                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["temperature"]["values"][0:-1] #delete all but one of the used temperature measures
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["soilMoisture"]["values"][0:-1] #delete all but one of the used soil moisture measures

                try:
                    with open("plantInformation.json","w") as outfile:
                        json.dump(information, outfile, indent=4)       #update the json file
                except FileNotFoundError:
                    print("WARNING: file opening error. The file doesn't exist")


    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.sensor_topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()


#DA INTEGRARE   
    # exposed=True
    # def GET(self, *uri,**params):
    ### PER POTER FORNIRE EVENTUALMENTE INFORMAZIONI AD ALTRI SERVIZI###

#DA INTEGRARE
    #def POST(self):
    ### PER POTER AGGIORNARE IL JSON CON NUOVE PIANTE SECONDO I BISGONI DELL'UTENTE ###



    def callWeatherService(self):
        """It gets precipitations informations from weather forecast service and extract 
        the daily precipitation sum from the json file received """
        #get_serviceCatalog_request=requests.get("")
        # get_weatherService_request=requests.get("http://127.0.0.1:8099/Irrigation")  #URL DA MODIFICARE CON QUELLO CHE SI OTTIENE DAL CATALOG
        # print("ciao")
        # print(get_weatherService_request.json())
        get_weatherService_request=json.load(open("outputWeatherForecast.json")) #per ora i dati sono presi da un file json esempio (ma in seguito saranno ricevuti tramite get_request)
        daily_precipitation_sum=get_weatherService_request["daily"]["precipitation_sum"][0]
        return daily_precipitation_sum 
        #E' NECESSARIO PREVEDERE UN MODO NEL WEATHER FORECAST DI INDICARE LE ZONE DEI CAMPI DI CIASCUNA COMPANY IN MODO DA AVERE INFORMAZIONI
        #PIU' SPECIFICHE



if __name__=="__main__":

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }
    irrigation=SmartIrrigation()
    irrigation.start()
    cherrypy.tree.mount(irrigation, "/Irrigation", conf)
    cherrypy.engine.start()
    
    while True:
        try:
            irrigation.control()
            time.sleep(30)
        except KeyboardInterrupt:
            irrigation.stop()
            cherrypy.engine.stop()
            break
