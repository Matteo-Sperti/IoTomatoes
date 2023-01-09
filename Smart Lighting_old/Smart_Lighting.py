import paho.mqtt.client as mqtt
import cherrypy
import time
from statistics import mean
import requests
import json

class SmartLighting:

    def __init__(self,serviceID="Smart Irrigation"):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        self.serviceID=serviceID
        self.sensor_topic="IoTomatoes/+/+/light/+/measure" #IoTomatoes/companyName/field/typeMeasure/deviceID/measure
        self.broker="test.mosquitto.org"
        self.port=1883

        self.message={
            "bn":"",
            "field":"",
            "command":"",
            "timeStamp":""
        }
        
        self.service_mqtt=mqtt.Client(serviceID,True)

        #CALL BACK
        self.service_mqtt.on_connect=self.myOnConnect
        self.service_mqtt.on_message=self.myOnMessage

    def start(self):
        """Connects and subscribes the sensor to the broker"""
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
        """Riceives measures from a specific topic and temporary storeS them in a
         json file for processing"""
        self.payload=json.loads(message.payload)
        #print(self.payload)
        
        companyName=self.payload["companyName"]
        fieldID=self.payload["field"]
        measure=self.payload["e"]["value"] #extract the measure value from MQTT message

        with open("lightInformation.json") as outfile:
            information=json.load(outfile)

        if companyName in information["company"]:
            position=information["company"].index(companyName)

            information["companyList"][position]["fields"][fieldID-1]["light"]["values"].append(measure) #insert the measure value in the json file
            information["companyList"][position]["fields"][fieldID-1]["light"]["lastUpdate"]=time.time() #update the lastUpdate value in the json file
        try:
            with open("lightInformation.json","w") as outfile:
                json.dump(information, outfile, indent=4)
        except FileNotFoundError:
            print("ERROR: file not found")


    def control(self):
        """Extracts measures from the json file, compute the mean value of each type of measure
        and perform the control function"""

        message=self.message

        try:
            with open("lightInformation.json") as outfile:
                information=json.load(outfile)          #extract all the information from the json
        except FileNotFoundError:
            print("ERROR: file not found")

        for company in information["companyList"]:
            companyName=company["companyName"]
            positionCompany=information["company"].index(companyName)   #indicates position index of the single company inside the list of all companies
            print(f"company={positionCompany+1}")

            for field in company["fields"]:
                message["command"]=""   #per ogni field il messaggio deve essere vuoto, altrimenti si considera di default il messaggio arrivato al campo precedente
                
                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                print(f"campo={fieldID}")
                minIdealLight=field["idealLight"]["min"]
                maxIdealLight=field["idealLight"]["max"]

                previousLight=field["light"]["previousValue"]

                #MODIFICA: DA FAR ESEGUIRE A MONGODB (IMPLEMENTARE GET PER RICEVERE LA MEDIA)
                try:
                    currentLight=round(mean(field["light"]["values"]),2)    #compute the mean value of received light measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
                
                #AGGIUNGERE INTEGRAZIONE CURRENTLIGHT CON QUELLA OTTENUTA DAL WEATHER FORECAST
                



                #CONTROL ALGORITHM:
                
                #CONTROLLO CONTINUO DURANTE TUTTA LA GIORNATA

                print(f"limite OFF={maxIdealLight}")
                print(f"limite ON={minIdealLight}")
                print(f"current value light={currentLight} lux")
                
                if currentLight>previousLight:
                    print("light sta aumentando")
                    if currentLight>=maxIdealLight:
                        print(f"""visto che light corrente:
                        {currentLight}>={maxIdealLight}""")
                        print("LUCI SPENTE")
                        message["command"]="OFF"
                        
                    else:
                        print(f"""visto che light corrente:
                        {currentLight}<{maxIdealLight}""")
                        print("LUCI ACCESE")
                        message["command"]="ON"
                        

                elif currentLight<previousLight:
                    print(f"light sta diminuendo, previousValue={previousLight}")
                    if currentLight<=minIdealLight:
                        print(f"""visto che il light corrente:
                        {currentLight}<={minIdealLight}""")
                        print("LUCI ACCESE")
                        message["command"]="ON"
                        
                    else:
                        print(f"""visto che light corrente:
                        {currentLight}>{minIdealLight}""")
                        print("LUCI SPENTE")
                        message["command"]="OFF"
                        
                else:
                    print("light costante")
                    if currentLight>maxIdealLight:
                        print("LUCI SPENTE")
                        message["command"]="OFF"
                        
                    elif currentLight<minIdealLight:
                        print("LUCI ACCESE")
                        message["command"]="ON"

                print("\n")   
                del information["companyList"][positionCompany]["fields"][fieldID-1]["light"]["values"][0:-1] #delete all but one of the used light measures

                with open("lightInformation.json","w") as outfile:
                    json.dump(information, outfile, indent=4)       #update the json file

    
    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.sensor_topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()


    






if __name__=="__main__":

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }
    lighting=SmartLighting()
    lighting.start()
    cherrypy.tree.mount(lighting, "/SmartLighting", conf)
    cherrypy.engine.start()
    
    while True:
        lighting.control()
        time.sleep(15)