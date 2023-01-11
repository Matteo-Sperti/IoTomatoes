import paho.mqtt.client as mqtt
import time
from statistics import mean
import requests
import json
import datetime



class SmartLighting:

    def __init__(self):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        self.serviceID="Lighting"
        self.commandTopic="IoTomatoes/"
        self.broker="test.mosquitto.org"
        self.port=1883

        self.message={
            "bn":"",
            "e":{
                "field":"",
                "command":"",
                "timeStamp":""
            }
        }
        
        self.service_mqtt=mqtt.Client(self.serviceID,True)

        #CALL BACK
        self.service_mqtt.on_connect=self.myOnConnect

    def start(self):
        """Connects and subscribes the sensor to the broker"""
        self.service_mqtt.connect(self.broker,self.port)
        self.service_mqtt.loop_start()
    
    def myOnConnect(self,client,userdata,flags,rc):
        """It provides information about Connection result with the broker"""
        dic={
            "0":f"Connection successful to {self.broker}",
            "1":f"Connection to {self.broker} refused - incorrect protocol version",
            "2":f"Connection to {self.broker} refused - invalid client identifier",
            "3":f"Connection to {self.broker} refused - server unavailable",
        }
             
        print(dic[str(rc)])


    def control(self):
        """It performs:
        - Call to resource catalog -> to retrieve information about each field for each company
        - Call to MongoDB to retrieve information about last hour measures (currentLigh) and previous hour measures 
          (previousLight)
        - Call to Weather forecast service to retrieve information about current cloudcover percentage, sunrise hour and sunset hour
        With these information it performs a simple control strategy to check if the light is under a fixed threshold"""

        message=self.message
        ####MODIFICA: inserire chiamata al resource catalog per ottenere le informazioni relative a
        #   -COMPANY
        #   -FIELD ID
        #   -TIPO DI PIANTA
        company="Andrea"
        fieldID=1
        plant="potatoes"
        message["e"]["command"]="" #per ogni field il messaggio deve essere vuoto


        try:
            with open("lightThreshold.json") as outfile:
                lightInfo=json.load(outfile)          
        except FileNotFoundError:
            print("ERROR: file not found")


        if plant in list(lightInfo.keys()):
            limits=lightInfo[plant]
            minLight=limits["lightLimit"]["min"]    #extract the ideal min value of light for the given plant from the json file 
            maxLight=limits["lightLimit"]["max"]    #extract the ideal max value of light for the given plant from the json file

        #IN FUTURO:
            # richiesta al service catalog per url mongodb e poi:
            # r=requests.get("URL_MONGODB/media?hour=1") ESPRIMERE BENE L'URL E I PARAMETRI IN RELAZIONE A COME COSTRUISCE IL SERVIZIO LUCA
            try:
                r=requests.get("http://127.0.0.1:8080/decreasing") #richiesta al MongoDBSimulator, da sostituire con il vero mongoDB
                r.raise_for_status()
            except requests.exceptions.InvalidURL as errURL:
                print(errURL)
            except requests.exceptions.HTTPError as errHTTP:
                print(errHTTP)
            except requests.exceptions.ConnectionError:
                print("503: Connection error. Server unavailable ")
            
            else:
                rValues=list((r.json()).values())
                previousLight=float(rValues[0])
                currentLight=float(rValues[1])
                
                currentHour=datetime.datetime.now().hour
                forecast=self.callWeatherService(currentHour)
                cloudCover=forecast[0]
                lightForecast=forecast[1]
                Sunrise=forecast[2]
                Sunset=forecast[3]
                
                currentLight=round((3*currentLight+lightForecast)/4,2) #integration sensor measure with the weather forecast one
                
                sunriseHour=int(Sunrise.split(":")[0]) #retrieves sunrise hour
                sunriseMinutes=int(Sunrise.split(":")[1]) #retrieves sunrise minutes
                sunrise=datetime.time(sunriseHour,sunriseMinutes,0)

                sunsetHour=int(Sunset.split(":")[0]) #retrieves sunset hour
                sunsetMinutes=int(Sunset.split(":")[1])#retrieves sunset minutes
                sunset=datetime.time(sunsetHour,sunsetMinutes,0)

                #currentTime=datetime.datetime.now().time
                currentTime=datetime.time(16,0,0) #per fare le prove
                

                
                #CONTROL ALGORITHM:
                #controllo DA SCHEDULARE dall'inizio dell'alba al tramonto (LA NOTTE NO, COSI SI LASCIA UN
                # CICLO LUCE/BUIO ALLE PIANTE PER LA FOTOSINTESI)
                if currentTime>=sunrise and currentTime<=sunset:

                    if cloudCover>=60:  #cosi se temporaneamente passa una nuvola che abbassa troppo il valore di luce non si accendono comunque
                        print("LIGHTING MAKE SENSE")
                        print(f"OFF threshold={maxLight}")
                        print(f"ON threshold={minLight}")
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
                    print("IT'S NIGHT")
                    print("light set to OFF")
                    message["e"]["command"]="OFF"
                
                message["bn"]=company
                message["e"]["field"]=fieldID
                message["e"]["timeStamp"]=time.time()
                
                print(f"message= {message}\n")

                #MODIFICA: INVIO MESSAGGIO A OGNI TOPIC DEL CAMPO
                commandTopic=self.commandTopic+str(company)+"/"+str(fieldID)+"/1/light"
                print(f"command Topic={commandTopic}\n\n")
                self.service_mqtt.publish(commandTopic,json.dumps(message))
        else:
            print("No crop with the specified name")



    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.sensor_topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()



    def callWeatherService(self,hour):
        """It gets precipitations informations from weather forecast service and extract:
            - daily precipitation sum
            - soil moisture forecast
            from the received json file"""
        ####MODIFICA: RICAVARE I DATI DAL WEATHER FORECAST ATTRAVERSO LA CHIAMATA AL SERVICE CATALOG
        # try:
        #     serviceCatalog_r=requests.get("") #richiesta al serviceCatalog per URL weather forecast
        #     serviceCatalog_r.raise_for_status()

        # except requests.exceptions.InvalidURL as errURL:
        #     print(errURL)
        # except requests.exceptions.HTTPError as errHTTP:
        #     print(errHTTP)
        # except requests.exceptions.ConnectionError:
        #     print("503: Connection error. Server unavailable ")

        # else:
        #     try:
        #         weatherService_r=requests.get("") #richiesta al weather forecast per le informazioni, restituisce un file json
        # except requests.exceptions.InvalidURL as errURL:
        #     print(errURL)
        # except requests.exceptions.HTTPError as errHTTP:
        #     print(errHTTP)
        # except requests.exceptions.ConnectionError:
        #     print("503: Connection error. Server unavailable ")

        #     else:
        #         weatherService_r=weatherService_r.json()
        
        #PER ORA I DATI SONO PRESI SEMPLICEMENTE DA UN FILE
        weatherService_r=json.load(open("outputLighting.json"))
        light=weatherService_r["hourly"]["sunLight"][hour]
        sunrise=weatherService_r["daily"]["sunrise"][0]
        sunset=weatherService_r["daily"]["sunset"][0]
        sunrise=sunrise.split("T")[1]
        sunset=sunset.split("T")[1]
        cloudCover=weatherService_r["hourly"]["cloudcover"][hour]
        
        return [cloudCover,light,sunrise,sunset] 
        



if __name__=="__main__":

    lighting=SmartLighting()
    lighting.start()

    
    while True:
        try:
            lighting.control()
            time.sleep(20)
        except KeyboardInterrupt:
            lighting.stop()
            break