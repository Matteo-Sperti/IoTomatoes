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
        


    def control(self):
        """Extracts measures from the json file, compute the mean value of each type of measure
        and perform the control law"""
        #CON MONGODB NON SAR' PIù NECESSARRIO ESTRARRE LE MISURE MA SEMPLICEMENTE IL VALORE MEDIO OTTENUTO DAL CLOUD
        message=self.message

        try:
            with open("plantInformation.json") as outfile:
                fileInfo=json.load(outfile)          #extract all the information from the json
        except FileNotFoundError:
            print("ERROR: file not found")

        for company in list(fileInfo["companyList"].keys()):
            print(f"Company={company}:")

            for field in fileInfo["companyList"][company]["fields"]:
                fieldIndex=fileInfo["companyList"][company]["fields"].index(field)
                message["command"]="" #per ogni field il messaggio deve essere vuoto, altrimenti si considera di default il messaggio arrivato al campo precedente

                fieldID=field["fieldID"]    #indicates position index of the field inside the list of all field for a single company 
                print(f"ID field={fieldID}")
                
                minSoilMoisture=field["soilMoistureLimit"]["min"]    #extract the ideal min value of soil moisture for the given plant from the json file 
                maxSoilMoisture=field["soilMoistureLimit"]["max"]    #extract the ideal max value of soil moisture for the given plant from the json file
                precipitationLimit=field["precipitationLimit"]["max"]
                previousSoilMoisture=field["soilMoistureMeasures"]["previousValue"]

                #MODIFICA: MEDIA DA RICAVARE DIRETTAMENTE COME GET DA MONGODB
                #in questo caso è assunta come già presente nel file
                currentSoilMoisture=field["soilMoistureMeasures"]["currentValue"]
                #IN FUTURO: 
                # r=requests.get("http://127.0.0.1:8081/media?hour=1") ESPRIMERE BENE L'URL E I PARAMETRI IN RELAZIONE A COME COSTRUISCE IL SERVIZIO LUCA
                # currentSoilMoisture=float(r.text)
                # print(currentSoilMoisture)

                #MODIFICA: UNA VOLTA IMPLEMENTATA BENE LA REQUEST IL CAMPO "currentValue" NEL FILE E' INUTILE. CANCELLARLO
                

                #CONTROL ALGORITHM:
                dailyPrecipitationSum=self.callWeatherService()
                
                #controllo schedulato per la sera (quindi sappiamo già complessivamente se durante il giorno ha piovuto)
                currentHour=datetime.datetime.now().hour
                if currentHour in list(range(00,24,1)): ###### MODIFICA: PORRE IL RANGE IN [21,24]
                    
                    #CONTROLLO PRECIPITAZIONI:
                    if dailyPrecipitationSum>precipitationLimit:
                        print("NON HA SENSO IRRIGARE")
                        print("pompe OFF")
                        message["command"]="OFF"
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

                message["bn"]=company
                message["field"]=fieldID
                message["timeStamp"]=time.time()
                
                print(f"message= {message}\n")
                
                commandTopic=self.commandTopic+str(company)+"/"+str(fieldID)+"/1/pump"
                print(f"command Topic={commandTopic}\n\n")
                self.service_mqtt.publish(commandTopic,json.dumps(message)) 
                
                #AGGIORNA L'ULTIMO VALORE DI MEDIA OTTENUTO:
                fileInfo["companyList"][company]["fields"][fieldIndex]["soilMoistureMeasures"]["previousValue"]=currentSoilMoisture 
                
                #### MODIFICA: NEL MOMENTO IN CUI LA MEDIA SARA' OTTENUTA DA MONGODB NON CI SARA' PIù BISOGNO DI CANCELLARE I DATI (CANCELLARE IL CAMPO
                # ANCHE DAL FILE JSON)
                #CANCELLA GLI ULTIMI DATI ADOPERATI PER IL CALCOLO DELLA MEDIA LASCIANDONE PER SICUREZZA SOLO 1
                #del fileInfo["companyList"][company]["fields"][fieldIndex]["soilMoistureMeasures"]["currentValues"][0:-1] #delete all but one of the used soil moisture measures

                try:
                    with open("plantInformation.json","w") as outfile:
                        json.dump(fileInfo, outfile, indent=4)       #update the json file
                except FileNotFoundError:
                    print("WARNING: file opening error. The file doesn't exist")


    def stop(self):
        """Unsubscribes and disconnects the sensor from the broker"""
        self.service_mqtt.unsubscribe(self.sensor_topic)
        self.service_mqtt.loop_stop()
        self.service_mqtt.disconnect()




    def callWeatherService(self):
        """It gets precipitations informations from weather forecast service and extract 
        the daily precipitation sum from the json file received """
        #get_serviceCatalog_request=requests.get("")
        # get_weatherService_request=requests.get("http://127.0.0.1:8099/Irrigation")  #URL DA MODIFICARE CON QUELLO CHE SI OTTIENE DAL CATALOG
        # print(get_weatherService_request.json())
        get_weatherService_request=json.load(open("outputWeatherForecast.json")) #per ora i dati sono presi da un file json esempio (ma in seguito saranno ricevuti tramite get_request)
        daily_precipitation_sum=get_weatherService_request["daily"]["precipitation_sum"][0]
        return daily_precipitation_sum 
        
        #### NOTAZIONE: E' NECESSARIO PREVEDERE UN MODO NEL WEATHER FORECAST DI INDICARE LE ZONE DEI CAMPI DI CIASCUNA COMPANY IN MODO DA AVERE INFORMAZIONI
        #PIU' SPECIFICHE
    

    exposed=True

    def GET(self, *uri, **params):
        """GET REST Method to provide information to the user about his own fields.
        Allowed commands:
        /getAll?company=<companyName> to retrieve information about all the field of a single company"""
        
        ####MODIFICA: AGGIORNARE CONSIDERANDO ANCHE I SISTEMI DI AUTORIZZAZIONE

        if len(uri)!=0:  
            if uri[0]=="getAll":    #AGGIUNGERE CONTROLLO ANCHE SUI PARAMETRI???????
                try:    
                    with open("plantInformation.json") as outfile:
                        fileInfo=json.load(outfile)
                except FileNotFoundError:
                    print("ERROR: file not found")

                parameters=list(params.values())
                if len(parameters)==1:
                    parameter1=parameters[0]
                    if parameter1 in list(fileInfo["companyList"].keys()):
                        return json.dumps(fileInfo["companyList"][parameter1], indent=4)
                    else:
                        
                        return "nessuna company trovata"
                else:
                    raise cherrypy.HTTPError(400,"BAD REQUEST: Please specify the company name as single parameter")
            else:
                raise cherrypy.HTTPError(404, "NOT FOUND: Please specify a valid URI")
        else:
            raise cherrypy.HTTPError(400,"BAD REQUEST: Please specify at least one URI")


    def POST(self, *uri, **params):
        """POST Rest method to insert a new company o field
        Allowed commands:
        /addField  to add a new field for the company 
        
        EXAMPLE OF BODY MESSAGE:
        {
            "companyName":"Andrea",
            "fieldID":2
            "plantType":"carote",
            "soilMoistureLimit":{"min":45, "max":60, "unit":"%"},
            "precipitationLimit":{"max":4,"unit":"mm"}
            }"""
        ####MODIFICA: STABILIRE LE AUTORIZZAZIONI
    
        if len(uri)!=0:
            if uri[0]=="insertField":
                try:
                    with open("plantInformation.json") as outfile:
                        fileInfo=json.load(outfile)
                except FileNotFoundError:
                    print("ERROR: file not found")
                
                newCompanyStructure={
                    "fieldsNumber": None,
                    "fieldIDList": [],
                    "fields": [
                        {
                            "fieldID": None,
                            "plantType": "",
                            "soilMoistureLimit": {
                                "min": None,
                                "max": None,
                                "unit": "%"
                            },
                            "precipitationLimit": {
                                "max": None,
                                "unit": "mm"
                            },
                            "soilMoistureMeasures": {
                                "currentValue": None,
                                "previousValue": None,
                                "unit": "%",
                                "lastUpdate": None
                            }
                        }
                        ]
                    }
                    
                newFieldInfo=json.loads(cherrypy.request.body.read())
                #estraggo le informazioni prinicipali ricevute nel body
                company=newFieldInfo["companyName"]
                newFieldID=newFieldInfo["fieldID"]
                newPlantType=newFieldInfo["plantType"]


                if newFieldID is not None and newFieldID.isnumeric(): #nessun errore nella scrittura del fieldID
                    #trasformo l'ID del campo in intero 
                    newFieldID=int(newFieldID)
                    #estrazione lista company e lista ID field per successivi controlli
                    companyList=list(fileInfo["companyList"].keys())
                    

                    if company in companyList: #la company è già presente
                        fieldIDList=list(fileInfo["companyList"][company]["fieldIDList"])
                        print(fieldIDList)
                        print(newFieldID)
                        if newFieldID in fieldIDList: #l'ID non è univoco
                            return f"FieldID is already present. Insert another fieldID different from: {fieldIDList}"
                        else:

                            #aggiorno le informazioni del new field che mi interessano
                            newCompanyStructure["fields"][0]["fieldID"]=newFieldID
                            newCompanyStructure["fields"][0]["plantType"]=newPlantType
                            newCompanyStructure["fields"][0]["soilMoistureLimit"]=newFieldInfo["soilMoistureLimit"]
                            newCompanyStructure["fields"][0]["precipitationLimit"]=newFieldInfo["precipitationLimit"]
                            newCompanyStructure["fields"][0]["soilMoistureMeasures"]["lastUpdate"]=time.time()
                            #inserisco le informazioni relativa al nuovo campo:
                            fileInfo["companyList"][company]["fields"].append(newCompanyStructure["fields"][0])
                            #aggiorno il numero di campo presenti e la lista degli ID
                            fileInfo["companyList"][company]["fieldIDList"].append(newFieldID)
                            fileInfo["companyList"][company]["fieldIDList"].sort()  #ordina la lista degli ID per restituirla sempre in ordine
                            fileInfo["companyList"][company]["fieldsNumber"]=len(fileInfo["companyList"][company]["fieldIDList"])
                            


                    else:   #la company non è ancora presente 

                        #aggiorno la informazioni del nuovo campo con i dati ricevuti
                        newCompanyStructure["fieldsNumber"]=1
                        newCompanyStructure["fieldIDList"].append(newFieldID)
                        newCompanyStructure["fields"][0]["fieldID"]=newFieldID
                        newCompanyStructure["fields"][0]["plantType"]=newPlantType
                        newCompanyStructure["fields"][0]["soilMoistureLimit"]=newFieldInfo["soilMoistureLimit"]
                        newCompanyStructure["fields"][0]["precipitationLimit"]=newFieldInfo["precipitationLimit"]
                        newCompanyStructure["fields"][0]["soilMoistureMeasures"]["lastUpdate"]=time.time()

            
                        #aggiungo il nome della company nella lista dei nomi
                        fileInfo["companyList"].update({company:newCompanyStructure})

                    try:
                        with open("plantInformation.json","w") as outfile:
                            json.dump(fileInfo,outfile,indent=4)
                        return "Succesfull field added "                
                    except FileNotFoundError:
                        print("ERROR: file not found")
                else:
                    return "insert a numeric integer fieldID"
            else:
                raise cherrypy.HTTPError(404, "NOT FOUND: Please specify a valid URI")
        else:
            raise cherrypy.HTTPError(400,"BAD REQUEST: Please specify at least one URI")



    def PUT(self, *uri, **params):
          """REST Method to update a field with new a new crop or soil moisture and precipitation limits
          Allowed commands:
        /updateField to add a new field for the company 

          EXAMPLE OF BODY MESSAGE:
        {
            "companyName":"Andrea",
            "
            "plantType":"carote",
            "soilMoistureLimit":{"max":60, "min":45, "unit":"%"}, 
            "precipitationLimit":{"max":4,"unit":"mm"}
            }"""

        ####MODIFICA: stabilire in base a cosa cercare (companyName e fieldID(?) ) per aggiornare il campo e autorizzazioni



    def DELETE(self, *uri, **params):
        """DELETE REST Method to delete a field or all the field of a specific company
        Allowed commands:
        /delete/all?company=<companyName> delete all the fields of a single company
        /delete/field?company=<NameCompany>&fieldID=<fieldID> delete """

        ####MODIFICA: stabilire in base a cosa cercare (companyName e fieldID(?) ) il campo  o la company da cancellare e autorizzazioni

        if len(uri)==2:
            try:
                with open("plantInformation.json") as outfile:
                    fileInfo=json.load(outfile)
            except FileNotFoundError:
                print("ERROR: file not found")

            companyList=list(fileInfo["companyList"].keys())
            parameters=list(params.values())
            if uri[0]=="delete" and uri[1]=="all":
                if len(parameters)==1:
                    companyToDelete=parameters[0]
                    if companyToDelete in companyList:
                        #cancello tutto il dizionario legato alla singola company
                        fileInfo["companyList"].pop(companyToDelete)

                        try:
                            with open("plantInformation.json","w") as outfile:
                                json.dump(fileInfo, outfile, indent=4)
                            return "Succesfull company deleted"
                        except FileNotFoundError:
                            print("ERROR: file not found")
                    else:
                        return "No company found"      
                else:
                    raise cherrypy.HTTPError(400, "BAD REQUEST: Please specify companyName as single parameter")
                    
            elif uri[0]=="delete" and uri[1]=="field":
                if len(parameters)==2:
                    companyToDelete=parameters[0]
                    fieldIDToDelete=int(parameters[1])
                    
                    if companyToDelete in companyList:
                        if fieldIDToDelete in fileInfo["companyList"][companyToDelete]["fieldIDList"]:
                            if len(fileInfo["companyList"][companyToDelete]["fieldIDList"])>1: #c'è pù di un field per la singola company, per cui cancello solo quel field
                                for field in fileInfo["companyList"][companyToDelete]["fields"]:
                                    if field["fieldID"]==fieldIDToDelete:
                                        #ricavo l'indice corrispondente al fieldID nella lista dei campi
                                        fieldIndex=fileInfo["companyList"][companyToDelete]["fields"].index(field)
                                        #elimino il field specifico
                                        fileInfo["companyList"][companyToDelete]["fields"].pop(fieldIndex)
                                        #aggiorno il numero dei campi presenti e la lista
                                        fileInfo["companyList"][companyToDelete]["fieldsNumber"]-=1
                                        fileInfo["companyList"][companyToDelete]["fieldIDList"].remove(fieldIDToDelete)
                                        break
                            else:   #c'è un unico field per la company. Per cui cancello direttamente tutta la company
                                fileInfo["companyList"].pop(companyToDelete)

                            try:
                                with open("plantInformation.json","w") as outfile:
                                    json.dump(fileInfo, outfile, indent=4)
                                return "Succesfull field deleted"
                            except FileNotFoundError:
                                print("ERROR: file not found") 
                        
                        else:
                            return "No fieldID found for the specified company"
                    else:
                        return "No company found"
                else:
                    raise cherrypy.HTTPError(400, "BAD REQUEST: Please specify companyName and fieldID as two only parameters")      
        
            else:
                raise cherrypy.HTTPError(404, "NOT FOUND: Please specify a valid URI")
        else:
            raise cherrypy.HTTPError(400,"BAD REQUEST: Please specify a valid URI")

        

        



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
            cherrypy.engine.block()
            break
