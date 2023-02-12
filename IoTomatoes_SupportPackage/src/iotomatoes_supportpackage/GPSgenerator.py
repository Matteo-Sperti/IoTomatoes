import random
import json
import requests

class GPSgenerator():
    def __init__(self, platformUrl : str, CompanyName : str, 
                    fileName : str = "TruckSettings.json"):
        """Initialize the GPS generator.
        
        Arguments:
		- `platformUrl (str)`: The url of the platform
        - `CompanyName (str)`: The name of the company
        - `fileName (str)`: The name of the file where the position is saved.
        Default is "TruckSettings.json"
        """
        self.fileName = fileName
        self.url = platformUrl
        self.CompanyName = CompanyName
        self.lat = -1
        self.lon = -1
        self.isFirstTime()

    def isFirstTime(self):
        """Check if the truck has a already saved position.
        If not, it will get the Company position from the platform."""

        info = json.load(open(self.fileName, 'r'))
        if "Location" in info:
            self.lat = info["Location"]["latitude"]
            self.lon = info["Location"]["longitude"]

        if self.lat == -1 and self.lon == -1:
            LocationDict = self.getCompanyLocation()
            if LocationDict is None:
                print("ERROR: Company location not found!")
                return
            else:
                self.lat = LocationDict["latitude"]
                self.lon = LocationDict["longitude"]
                self.savePosition()

    def getCompanyLocation(self):
        """Get the company location from the catalog."""
        try:
            res = requests.get(self.url + "/" + self.CompanyName + "/location")
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
        """Generate a random path for the truck."""
        max_deviation = 0.01 # 1.1 meter
        
        self.lat = self.lat + random.uniform(-max_deviation, max_deviation)
        self.lon = self.lon + random.uniform(-max_deviation, max_deviation)
              
    def TruckStop(self):
        """Stop the truck."""
        self.savePosition()

    def savePosition(self):
        """Save the truck position in the file."""
        dict = json.load(open(self.fileName))
        dict["Location"]["latitude"] = self.lat
        dict["Location"]["longitude"] = self.lon
        json.dump(dict,open(self.fileName,"w"))

    def get_position(self):
        """Move the truck and return the truck position."""
        self.randomPath()        
        return {"latitude":self.lat,"longitude":self.lon}