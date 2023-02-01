import random
import json
import math

class Tractor():
    def __init__(self):
        settings = json.load(open('TruckSettings.json'))
        self.lat = settings["Location"]["latitude"]
        self.lon = settings["Location"]["longitude"]
        self.trace = {"latitude":[],"longitude":[]}

    def isFirstTime(self):
        if self.lat == 0 and self.lon == 0:
            # ask catalog for company location center and set it as start location
            # next time the truck will start from there
            pass

    def randomPath(self):
        #generate random path and publish it

        max_deviation = 0.01 # 1.1 meter
        
        self.lat = self.lat + random.uniform(-max_deviation, max_deviation)
        self.lon = self.lon + random.uniform(-max_deviation, max_deviation)
        self.trace["latitude"].append(self.lat)
        self.trace["longitude"].append(self.lon)
        print(self.trace)
        #self.myPublish(self.topic,json.dumps(dict))
        
    def shape(self,num_points):
        for i in range(num_points):
            freq = math.pi/32*i
            self.lat = 16*math.sin(freq)**3
            self.lon = 13*math.cos(freq) - 5*math.cos(2*freq) - 2*math.cos(3*freq) - math.cos(4*freq)
            self.trace["latitude"].append(self.lat)
            self.trace["longitude"].append(self.lon)
            
    def TruckStop(self):
        #publish stop message
        dict = json.load(open('TruckSettings.json'))
        dict["Location"]["latitude"]=self.lat
        dict["Location"]["longitude"] = self.lon
        
        json.dump(dict,open('TruckSettings.json',"w"))
        
        json.dump(self.trace,open('trace.json',"w"))
        


        
        