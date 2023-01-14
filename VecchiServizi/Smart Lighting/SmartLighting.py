import paho.mqtt.client as mqtt
import cherrypy
import time
from statistics import mean
import json
import sys
from socket import gethostname, gethostbyname

sys.path.append("../SupportClasses/")
from GenericEndpoint import GenericEndpoint

class SmartLighting(GenericEndpoint):

    def __init__(self,settings : dict):
        """Inizializzazione della classe del servizio (da adattare in seguito)"""

        super().__init__(settings, isService=True)
        
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

    def notify(self,topic,message):
        """Riceives measures from a specific topic and temporary stores them in a
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


    def control(self):
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
                idealLight=field["lux"]      #extract the ideal value of light for the given plant from the json file

                try:
                    meanLight=mean(field["lightMeasures"]["values"])    #compute the mean value of received light measures
                except:
                    print("MeanError: necessario almeno un dato per il calcolo della media")
                else:
                    #CONTROL ALGORITHM:
                    if (meanLight<idealLight):
                        print(f"""
                        Average light={meanLight}
                        Accendi luci campo {fieldID} ({plant}) di {companyName}""")
                            #self.service_mqtt.publish(topic_attuatori) 
                    else:
                        print(f"""
                        Average light={meanLight}
                        Spegni luci campo {fieldID} ({plant}) di {companyName}""")
                        #self.service_mqtt.publish(topic_attuatori)
                        
                    del information["companyList"][positionCompany]["fields"][fieldID-1]["lightMeasures"]["values"][0:-1] #delete all but one of the used light measures

                    with open("lightInformation.json","w") as outfile:
                        json.dump(information, outfile, indent=4)       #update the json file


    # def sendCommand(self):
    #     message=self.actuator_message
    #     if len(self.measure)>=12:
    #         self.media=mean(self.measure)
    #         if self.media<65:
    #             message["e"]["command"]="ON"
    #         else:
    #             message["e"]["command"]="OFF"

    #         self.service_mqtt.publish(self.actuator_topic,json.dumps(message),2)
    #         print(f"Published\n {message}")
    #         self.measure=[]

    # def callResourceCatalog(self):
    #     parameters={"deviceIdToSearch":self.sensorID}
    #     get_device_request=requests.get(f"URL resource catalog", parameters)
    #     print(get_device_request.json())
    #     topic=get_device_request.json()[""]

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
    settings = json.load(open("SmartLightingSettings.json", "r"))

    ip_address = gethostbyname(gethostname())
    port = settings["IPport"]
    settings["IPaddress"] = ip_address

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }


    lighting=SmartLighting(settings)
    lighting.start()

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
        print("SmartLighting stopped")