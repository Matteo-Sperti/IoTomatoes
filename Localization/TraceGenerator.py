import json
from GenericEndpoint import GenericEndpoint
import requests

class TraceGenerator(GenericEndpoint):
    def __init__(self):
        settings = json.load(open('settings.json'))
        self.create_url = settings["create_url"]
        self.view_url = settings["view_url"]
        self.lat=[]
        self.lon=[]
        self.trackpoints = ""
        super().__init__(settings, True, False)
        self.gpx_template   = """<?xml version="1.0" encoding="UTF-8"?>
        <gpx version="1.1" creator="Python GPX Generator">

            <trk>
            <trkseg>
                {trackpoints}
        </trkseg>
        </trk>
        </gpx>"""

    def notify(self, topic,payload):
        self.lat.append(payload["latitude"])
        self.lon.append(payload["longitude"])
    
    def GenerateGPX(self):
        for i in range(len(self.lat)):
                self.trackpoints += f"<trkpt lat='{self.lat}' lon='{self.lon}'></trkpt>\n"
        gpx = self.gpx_template.format(trackpoints=self.trackpoints)
        response = requests.post(self.create_url, data=gpx)
        gpx_id = response.text
        return (self.view_url+f'/{gpx_id}')


         
        
