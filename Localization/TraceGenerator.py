import json
from GenericEndpoint import GenericEndpoint
import requests
import gpxpy
import folium
class TraceGenerator(GenericEndpoint):
    def __init__(self):
        settings = json.load(open('settingsTraceGenerator.json',"r"))
        self.create_url = settings["create_url"]
        self.view_url = settings["view_url"]
        self.pswd = settings["password"]
        dict=json.load(open('trace.json',"r"))
        self.lat=dict["latitude"]
        self.lon=dict["longitude"]
        self.trackpoints = ""
        #super().__init__(settings, True, False)
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
                self.trackpoints += f"<trkpt lat='{self.lat[i]}' lon='{self.lon[i]}'></trkpt>\n"
        gpx_file = self.gpx_template.format(trackpoints=self.trackpoints)
  
        gpx=gpxpy.parse(gpx_file)
        first_point = gpx.tracks[0].segments[0].points[0]
        map = folium.Map(location=[first_point.latitude, first_point.longitude])

        # Add GPX track as a polyline on the map
        lat_lons = [(p.latitude, p.longitude) for p in gpx.tracks[0].segments[0].points]
        folium.PolyLine(lat_lons, color='red', weight=2.5, opacity=1).add_to(map)

        # Show map
        map.save("map.html")
       
if __name__ == "__main__":
        tg = TraceGenerator()
        tg.GenerateGPX()

         
        
