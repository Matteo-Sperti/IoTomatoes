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
        
        ### ANCORA DA DEFINIRE BENE  ###
        # self.actuatorID="Luce1"
        # self.actuator_topic="IoTomatoes/Andrea/Luce1/Command"
        # self.actuator_message={
        #             "bn":self.actuatorID,
        #             "e": {
        #                     "name":"attuatore",
        #                     "command":"ON"
        #     }
        # }

        # self.measure=[]
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

            information["companyList"][position]["fields"][fieldID-1]["lightMeasures"]["values"].append(measure) #insert the measure value in the json file
            information["companyList"][position]["fields"][fieldID-1]["lightMeasures"]["lastUpdate"]=time.time() #update the lastUpdate value in the json file
        
        with open("lightInformation.json","w") as outfile:
            json.dump(information, outfile, indent=4)


    def controlAlgorithm(self):
        """Extracts measures from the json file, compute the mean value of each type of measure
        and perform the control function"""

        with open("lightInformation.json") as outfile:
            information=json.load(outfile)          #extract all the information from the json

        for company in information["companyList"]:
            companyName=company["companyName"]
            positionCompany=information["company"].index(companyName)   #indicates position index of the single company inside the list of all companies
            print(f"company={positionCompany}")

            for field in company["fields"]:
                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                plant=field["plantType"]
                print(f"campo={fieldID}")
                idealLight=field["idealLight"]      #extract the ideal value of light for the given plant from the json file

                try:
                    currentLight=mean(field["lightMeasures"]["values"])    #compute the mean value of received light measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
                
                #CONTROL ALGORITHM:
                

                # if (currentLight<idealLight):
                #     print(f"""
                #     Average light={currentLight}
                #     Accendi luci campo {fieldID} ({plant}) di {companyName}""")
                #         #self.service_mqtt.publish(topic_attuatori) 
                # else:
                #     print(f"""
                #     Average light={currentLight}
                #     Spegni luci campo {fieldID} ({plant}) di {companyName}""")
                #     #self.service_mqtt.publish(topic_attuatori)
                    
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lightMeasures"]["values"][0:-1] #delete all but one of the used light measures

                with open("lightInformation.json","w") as outfile:
                    json.dump(information, outfile, indent=4)       #update the json file

    
    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.sensor_topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()


    

#DA CAPIRE ANCORA COME IMPLEMENTARE LA CHIAMATA AL RESOURCE CATALOG PER OTTENERE I TOPIC DI OGNI LUCE E SENSORE CREPUSCOLARE
    # def callWeatherService(self):
    #     parameters={"":}
    #     get_service_request=requests.get(f"URL Service catalog", parameters)
    #     print(get_device_request.json())
    #     weather_URL=get_service_request.json()[""]

#DA CAPIRE ANCORA COME IMPLEMENTARE LA CHIAMATA AL WEATHER FORECAST PER OTTENERE DATI SULLA LUMINOSITA'
    # exposed=True
    # def GET(self, *uri,**params):
    #     """Provides information to other webServices"""
    


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
        lighting.controlA()
        time.sleep(30)