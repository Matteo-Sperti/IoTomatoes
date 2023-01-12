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