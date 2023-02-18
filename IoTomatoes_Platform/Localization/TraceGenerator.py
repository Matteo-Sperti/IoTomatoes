import json
import gpxpy
import folium
import cherrypy
import time
import signal
import requests
import imgkit
import base64

from iotomatoes_supportpackage import BaseService, web_exception, setREST


class TraceGenerator(BaseService):
    def __init__(self, settings: dict, MongoDbUrl: str):
        """Constructor of the TraceGenerator class.

        Arguments:
        - `settings (dict)`: Dictionary containing the settings of the service.
        - `MongoDbUrl (str)`: Url of the MongoDB service.
        """

        self.create_url = settings["create_url"]
        self.view_url = settings["view_url"]
        self.pswd = settings["password"]
        self.MongoDbUrl = MongoDbUrl

        self.gpx_template = """<?xml version="1.0" encoding="UTF-8"?>
		<gpx version="1.1" creator="Python GPX Generator">
			<trk>
                <trkseg>
                    {trackpoints}
                </trkseg>
		    </trk>
		</gpx>"""

    def TrucksPosition(self, CompanyName: str):
        """Get the position of all the trucks of a company.

        Arguments:
        - `CompanyName (str)`: Name of the company.

        Returns a dictionary containing a base64 encoded image.
        """

        fileNameHtlm = "mapPositions.html"
        fileNamePng = "mapPositionsImage.png"
        try:
            response = requests.get(
                f"{self.MongoDbUrl}/{CompanyName}/trucksPosition")
            response.raise_for_status()
            dict_ = response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                raise web_exception(404, "No trucks found")
            else:
                raise web_exception(
                    err.response.status_code, err.response.reason)
        except:
            raise web_exception(500, "Error getting data from the database")

        LatCenter = sum([dict_[id]["latitude"]
                        for id in dict_.keys()]) / len(dict_.keys())
        LonCenter = sum([dict_[id]["longitude"]
                        for id in dict_.keys()]) / len(dict_.keys())

        map = folium.Map(location=[LatCenter, LonCenter])
        for key in dict_.keys():
            folium.Marker([dict_[key]["latitude"], dict_[key]
                           ["longitude"]], popup="Truck " + key).add_to(map)
        map.save("mapPositions.html")
        imgkit.from_file(fileNameHtlm, fileNamePng)
        with open(fileNamePng, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())

        out = {"img64": encoded_string.decode("utf-8")}
        return json.dumps(out)

    def GenerateGPX(self, CompanyName: str, truckID: str):
        """Generate a GPX file from the trace of a truck.

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `truckID (str)`: ID of the truck.

        Returns a dictionary containing a base64 encoded image.
        """

        fileNameHtlm = "mapTrace.html"
        fileNamePng = "mapTraceImage.png"
        try:
            response = requests.get(
                f"{self.MongoDbUrl}/{CompanyName}/{truckID}/trace")
            response.raise_for_status()
            dict_ = response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                raise web_exception(404, "No trucks found")
            else:
                raise web_exception(
                    err.response.status_code, err.response.reason)
        except:
            raise web_exception(500, "Error getting data from the database")

        lat = dict_["latitude"]
        lon = dict_["longitude"]
        trackpoints = ""
        for i in range(len(lat)):
            trackpoints += f"<trkpt lat='{lat[i]}' lon='{lon[i]}'></trkpt>\n"
        gpx_file = self.gpx_template.format(trackpoints=trackpoints)

        gpx = gpxpy.parse(gpx_file)
        first_point = gpx.tracks[0].segments[0].points[0]
        map = folium.Map(
            location=[first_point.latitude, first_point.longitude])
        # Add GPX track as a polyline on the map
        lat_lons = [(p.latitude, p.longitude)
                    for p in gpx.tracks[0].segments[0].points]
        folium.PolyLine(lat_lons, color='red',
                        weight=2.5, opacity=1).add_to(map)
        folium.Marker([lat[-1], lon[-1]], popup="Truck " + truckID).add_to(map)

        # Show map
        map.save(fileNameHtlm)

        options = {
            'quiet': ''
            }
        encoded_string = imgkit.from_file(fileNameHtlm, False, options=options)

        out = {"img64": encoded_string.decode("utf-8")}
        return json.dumps(out)


class LocalizationWebService(BaseService):
    exposed = True

    def __init__(self, settings: dict):
        """Constructor of the class"""

        super().__init__(settings)
        if "MongoDB_ServiceName" in settings:
            self.mongoToCall = settings["MongoDB_ServiceName"]
        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
        self.traceGen = TraceGenerator(
            settings, mongoDB_url)

    def GET(self, *uri, **params):
        """GET method of the REST API

        Allowed URIs:
        - `/<CompanyName>/<TruckID>/trace`: returns the trace of the truck in a map.
        - `/<CompanyName>/trucksPosition`: returns the position of the trucks in a map
        """
        try:
            if len(uri) == 3 and uri[2] == "trace":
                return self.traceGen.GenerateGPX(uri[0], uri[1])
            if len(uri) == 2 and uri[1] == "trucksPosition":
                return self.traceGen.TrucksPosition(uri[0])
            else:
                raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")


def sigterm_handler(signal, frame):
    WebService.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    settings = json.load(open("TraceGeneratorSettings.json"))

    ip_address, port = setREST(settings)

    WebService = LocalizationWebService(settings)
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(WebService, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    while True:
        time.sleep(5)
