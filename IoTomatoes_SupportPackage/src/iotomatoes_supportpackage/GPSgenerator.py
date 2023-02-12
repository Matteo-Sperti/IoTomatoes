import random
import json
import requests

class GPSgenerator():
    def __init__(self, platformUlr : str, CompanyName : str, 
                    fileName : str = "TruckSettings.json"):
        self.fileName = fileName
        settings = json.load(open(self.fileName, 'r'))
        self.lat = settings["Location"]["latitude"]
        self.lon = settings["Location"]["longitude"]
        self.isFirstTime(platformUlr, CompanyName)

    def isFirstTime(self, ResourceCatalog_url, Company_name):
        if self.lat == -1 and self.lon == -1:
            LocationDict = self.getCompanyLocation(ResourceCatalog_url, Company_name)
            if LocationDict is None:
                print("ERROR: Company location not found!")
                return
            else:
                self.lat = LocationDict["latitude"]
                self.lon = LocationDict["longitude"]
                self.savePosition()

    def getCompanyLocation(self, ResourceCatalog_url : str, CompanyName : str):
        try:
            res = requests.get(ResourceCatalog_url + "/" + CompanyName + "/location")
            res.raise_for_status()
            res_dict = res.json()
        except Exception as e:
            print(e)
            return None
        else:
            if "latitude" not in res_dict or "longitude" not in res_dict:
                print("ERROR: Company location not found!")
                return None
            return res_dict

    def randomPath(self):
        max_deviation = 0.01 # 1.1 meter
        
        self.lat = self.lat + random.uniform(-max_deviation, max_deviation)
        self.lon = self.lon + random.uniform(-max_deviation, max_deviation)
              
    def TruckStop(self):
        self.savePosition()

    def savePosition(self):
        dict = json.load(open(self.fileName))
        dict["Location"]["latitude"] = self.lat
        dict["Location"]["longitude"] = self.lon
        json.dump(dict,open(self.fileName,"w"))

    def get_position(self):
        self.randomPath()        
        return {"latitude":self.lat,"longitude":self.lon}