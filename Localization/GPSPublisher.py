import random
import requests
import json
from GenericEndpoint import GenericEndpoint
import requests

class Tractor(GenericEndpoint):
    def __init__(self):
        settings = json.load(open('settings.json'))
        super().__init__(settings, False, True)
        self.startlat = settings["lastKnownLocation"]["latitude"]
        self.startlon = settings["lastKnownLocation"]["longitude"]
        self.topic = settings["publishTopics"]
        #ask catalog for company location and publish there
    def isFirstTime(self):
        if self.startlat == 0 and self.startlon == 0:
            #ask catalog for company location center and set it as start location
            # next time the truck will start from there
            pass
    def randomPath(self):
        #generate random path and publish it
        lat = self.startlat
        lon = self.startlon
        max_deviation = 0.00001 # 1.1 meter
        
        lat = self.start_lat + random.uniform(-max_deviation, max_deviation)
        lon = self.start_lon + random.uniform(-max_deviation, max_deviation)
        dict = {"latitude":lat,"longitude":lon}
        self.myPublish(self.topic,json.dumps(dict))
        
        
        