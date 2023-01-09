import paho.mqtt.client as mqtt
import cherrypy
import time
import json
from statistics import mean
import requests
import datetime


class SmartIrrigation:

    def __init__(self):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""

        self.serviceID="Irrigation"
        self.sensor_topic="IoTomatoes/+/+/+/measure" #IoTomatoes/companyName/field/deviceID/measure
        self.commandTopic="IoTomatoes/"
        self.broker="test.mosquitto.org"
        self.port=1883

        self.message={
            "bn":"",
            "field":"",
            "command":"",
            "timeStamp":""
        }
        
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
        unit=self.payload["e"]["unit"]
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

        message=self.message

        try:
            with open("plantInformation.json") as outfile:
                information=json.load(outfile)          #extract all the information from the json
        except FileNotFoundError:
            print("WARNING: file opening error. The file doesn't exist")

        for company in information["companyList"]:
            companyName=company["companyName"]
            positionCompany=information["company"].index(companyName)   #indicates position index of the single company inside the list of all companies
            print(f"company={positionCompany+1}")

            for field in company["fields"]:
                message["command"]="" #per ogni field il messaggio deve essere vuoto, altrimenti si considera di default il messaggio arrivato al campo precedente

                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                print(f"campo={fieldID}")
                
                minSoilMoisture=field["soilMoistureLimit"]["min"]    #extract the ideal min value of soil moisture for the given plant from the json file 
                maxSoilMoisture=field["soilMoistureLimit"]["max"]    #extract the ideal max value of soil moisture for the given plant from the json file
                precipitationLimit=field["precipitationLimit"]["max"]
                
                
                previousSoilMoisture=field["lastMeasures"]["soilMoisture"]["previousValue"]

                #MODIFICA: DA FAR ESEGUIRE A MONGODB
                try:
                    currentSoilMoisture=mean(field["lastMeasures"]["soilMoisture"]["values"])  #compute the mean value of received soil Moisture measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
                

                
                
                #CONTROL ALGORITHM:
                dailyPrecipitationSum=self.callWeatherService()
                
                #controllo schedulato per la sera (quindi sappiamo già complessivamente se durante il giorno ha piovuto)
                
                currentHour=datetime.datetime.now().hour
                if currentHour in list(range(00,24,1)): ###### MODIFICARE RANGE IN [21,24]
                    
                    #CONTROLLO PRECIPITAZIONI:
                    if dailyPrecipitationSum>precipitationLimit:
                        print("NON HA SENSO IRRIGARE")
                        print("pompe OFF")
                    else:
                        print("HA SENSO IRRIGARE")
                        
                        # HYSTERESIS CONTROL LAW (SOILMOISTURE):
                        # DOPO IL CONTROLLO DELLA PIOGGIA O MENO, SI ASSUME CHE L'INCREMENTO DELL'UMIDITA' SIA
                        # LEGATA SOLO ALLA NOSTRA IRRIGAZIONE E NON A FENOMENI ESTERNI
        
                        

                        print(f"limite OFF={maxSoilMoisture}")
                        print(f"limite ON={minSoilMoisture}")
                        print(f"current value soil moisture={currentSoilMoisture}")
                        
                        if currentSoilMoisture>previousSoilMoisture:
                            print("soilMoisture sta aumentando")
                            if currentSoilMoisture>=maxSoilMoisture:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}>={maxSoilMoisture}""")
                                print("POMPE SPENTE")
                                message["command"]="OFF"
                                
                            else:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}<{maxSoilMoisture}""")
                                print("POMPE ACCESE")
                                message["command"]="ON"
                               

                        elif currentSoilMoisture<previousSoilMoisture:
                            print(f"soilMoisture sta diminuendo, previousValue={previousSoilMoisture}")
                            if currentSoilMoisture<=minSoilMoisture:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}<={minSoilMoisture}""")
                                print("POMPE ACCESE")
                                message["command"]="ON"
                                
                            else:
                                print(f"""visto che il soil moisture corrente:
                                {currentSoilMoisture}>{minSoilMoisture}""")
                                print("POMPE SPENTE")
                                message["command"]="OFF"
                                
                        else:
                            print("soil moisture costante")
                            if currentSoilMoisture>maxSoilMoisture:
                                print("POMPE SPENTE")
                                message["command"]="OFF"
                                
                            elif currentSoilMoisture<minSoilMoisture:
                                print("POMPE ACCESE")
                                message["command"]="ON"
                                  
                            
                else:
                    print("non è tempo di irrigare")
                    print("POMPE SPENTE")
                    message["command"]="OFF"

                message["bn"]=companyName
                message["field"]=fieldID
                message["timeStamp"]=time.time()
                print("")
                print(f"{message}")
                print("")

                commandTopic=self.commandTopic+str(companyName)+"/"+str(fieldID)+"/1/pump"
                print(commandTopic)
                self.service_mqtt.publish(commandTopic,json.dumps(message)) 
                #AGGIORNA L'ULTIMO VALORE DI MEDIA OTTENUTO:
                information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["soilMoisture"]["previousValue"]=currentSoilMoisture 
                
                #CANCELLA GLI ULTIMI DATI ADOPERATI PER IL CALCOLO DELLA MEDIA LASCIANDONE PER SICUREZZA SOLO 1
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
    #exposed=True
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
            time.sleep(20)
        except KeyboardInterrupt:
            irrigation.stop()
            cherrypy.engine.stop()
            break
