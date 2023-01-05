import paho.mqtt.client as mqtt
import cherrypy
import time
import json
from statistics import mean


class SmartIrrigation:

    def __init__(self,serviceID="Smart Irrigation"):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""
        self.serviceID=serviceID
        self.sensor_topic="IoTomatoes/+/+/+/+/measure" #IoTomatoes/companyName/field/typeMeasure/deviceID/measure
        self.broker="test.mosquitto.org"
        self.port=1883

        
        self.service_mqtt=mqtt.Client(serviceID,True)

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
        
        with open("plantInformation.json","w") as outfile:
            json.dump(information, outfile, indent=4)
        

    def control(self):
        """Extracts measures from the json file, compute the mean value of each type of measure
        and perform the control function"""

        with open("plantInformation.json") as outfile:
            information=json.load(outfile)          #extract all the information from the json
        
        for company in information["companyList"]:
            companyName=company["companyName"]
            positionCompany=information["company"].index(companyName)   #indicates position index of the single company inside the list of all companies
            print(f"company={positionCompany}")

            for field in company["fields"]:
                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                plant=field["plantType"]
                print(f"campo={fieldID}")
                minTemperature=field["temperature"][0]      #extract the ideal min value of temperature for the given plant from the json file
                maxTemperature=field["temperature"][1]      #extract the ideal max value of temperature from the given plant json file
                minSoilMoisture=field["soilMoisture"][0]    #extract the ideal min value of soil moisture for the given plant from the json file 
                maxSoilMoisture=field["soilMoisture"][1]    #extract the ideal max value of soil moisture for the given plant from the json file
                try:
                    meanTemperature=mean(field["lastMeasures"]["temperature"]["values"])    #compute the mean value of received temperature measures
                    meanSoilMoisture=mean(field["lastMeasures"]["soilMoisture"]["values"])  #compute the mean value of received soil Moisture measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
            
                # print(meanTemperature)
                # print(meanSoilMoisture)

                #CONTROL ALGORITHM:
                if (meanTemperature<=maxTemperature and meanTemperature>=minTemperature)and(meanSoilMoisture<=maxSoilMoisture and meanSoilMoisture>=minSoilMoisture):
                    print(f"""
                    Average temperature={meanTemperature}
                    Average soil moisture={meanSoilMoisture}
                    Accendi pompe campo {fieldID} ({plant}) di {companyName}""")
                        #self.service_mqtt.publish(topic_attuatori) 
                else:
                    print(f"""
                    Average temperature={meanTemperature}
                    Average soil moisture={meanSoilMoisture}
                    Spegni pompe campo {fieldID} ({plant}) di {companyName}""")
                    #self.service_mqtt.publish(topic_attuatori)
                    
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["temperature"]["values"][0:-1] #delete all but one of the used temperature measures
                del information["companyList"][positionCompany]["fields"][fieldID-1]["lastMeasures"]["soilMoisture"]["values"][0:-1] #delete all but one of the used soil moisture measures

                with open("plantInformation.json","w") as outfile:
                    json.dump(information, outfile, indent=4)       #update the json file
                


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

#DA INTEGRARE
    # def callResourceCatalog(self):
    #     parameters={"deviceIdToSearch":self.sensorID}
    #     get_device_request=requests.get(f"URL resource catalog", parameters)
    #     print(get_device_request.json())
    #     topic=get_device_request.json()[""]

#DA INTEGRARE
    # def callWeatherService(self):
    #     parameters={"":}
    #     get_service_request=requests.get(f"URL Service catalog", parameters)
    #     print(get_device_request.json())
    #     weather_URL=get_service_request.json()[""]

    


if __name__=="__main__":

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }
    irrigation=SmartIrrigation()
    irrigation.start()
    cherrypy.tree.mount(irrigation, "/SmartIrrigation", conf)
    cherrypy.engine.start()

    while True:
        irrigation.control()
        time.sleep(30)
