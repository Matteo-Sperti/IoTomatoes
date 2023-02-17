import requests
import json
import time
import cherrypy
import signal

from iotomatoes_supportpackage import BaseService, web_exception, setREST


class WeatherApp:
    """Handles the weather requests"""

    def __init__(self, ResourceCatalogUrl: str, weatherUrl: str, IrrigationDict: dict, LightingDict: dict):
        """Constructor of the class

        Arguments:
        - `ResourceCatalogUrl (str)`: the url of the Resource Catalog
        - `weatherUrl (str)`: the url of the weather API
        - `IrrigationDict (dict)`: the dictionary containing the parameters for the irrigation service
        - `LightingDict (dict)`: the dictionary containing the parameters for the lighting service
        """

        self.ResourceCatalogUrl = ResourceCatalogUrl
        self.weatherUrl = weatherUrl
        self.IrrigationDict = IrrigationDict
        self.LightingDict = LightingDict

    def makeRequest(self, dictInput):
        """handles an API request based on the JSON input file (forwards a getRequest to the weather API)"""
        try:
            # makes the request, the parameters are in the input file
            response = requests.get(self.weatherUrl, params=dictInput)
            response.raise_for_status()  # checks if the request was successful
            res_dict = response.json()
        except:
            print("Error in the Weather API")
            return None
        else:
            return res_dict

    def getLocation(self, CompanyName: str):
        """Gets the location of the company from the Resource Catalog"""
        try:
            response = requests.get(
                f"{self.ResourceCatalogUrl}/{CompanyName}/location")
            response.raise_for_status()
            res_dict = response.json()["Location"]
            latitude = res_dict["latitude"]
            longitude = res_dict["longitude"]
        except:
            print("Error in the Resource Catalog")
            return None, None
        else:
            return latitude, longitude

    def IrrigationData(self, CompanyName: str):
        """Gets the data from the weather API for the irrigation service"""

        latitude, longitude = self.getLocation(CompanyName)
        if latitude is None or longitude is None:
            return {}

        InputDict = self.IrrigationDict.copy()
        InputDict["latitude"] = latitude
        InputDict["longitude"] = longitude
        response = self.makeRequest(InputDict)
        if response is None:
            return {}

        return response  # DA SISTEMARE

    def LightingData(self, CompanyName: str):
        """Gets the data from the weather API for the lighting service"""

        latitude, longitude = self.getLocation(CompanyName)
        if latitude is None or longitude is None:
            return {}

        InputDict = self.LightingDict.copy()
        InputDict["latitude"] = latitude
        InputDict["longitude"] = longitude
        response = self.makeRequest(InputDict)
        if response is None:
            return {}

        listToBeConverted = (response["hourly"].pop("shortwave_radiation"))
        # converts the shortwave radiation to lux
        convertedList = [x/0.0079 for x in listToBeConverted]
        response["hourly"]["Illumination"] = convertedList
        listToBeConverted = response["daily"].pop("shortwave_radiation_sum")
        # converts the shortwave radiation to lux
        convertedList = [x/0.0079 for x in listToBeConverted]
        response["daily"]["Illumination_sum"] = convertedList
        response["hourly_units"]["Illumination"] = "lux"
        response["hourly_units"].pop("shortwave_radiation")
        response["daily_units"]["Illumination_sum"] = "lux"
        response["daily_units"].pop("shortwave_radiation_sum")
        return response


class WheaterService(BaseService):
    exposed = True

    def __init__(self, settings:  dict):
        """ Constructor of the class

        Arguments:
        `settings (dict)`: the settings of the service
        """
        super().__init__(settings)
        self.weather = WeatherApp(self.ResourceCatalog_url, settings["WeatherUrl"],
                                  settings["IrrigationDict"], settings["LightingDict"])

    def GET(self, *uri, **params):
        """Handles the GET requests

        Allowed URLs:
        - /<CompanyName>/Irrigation to get the data for the irrigation service
        - /<CompanyName>//Lighting to get the data for the lighting service
        """
        if len(uri) != 2:
            raise cherrypy.HTTPError(
                404, "Please specify the service you want to use")
        else:
            if uri[0] == "irrigation":
                return json.dumps(self.weather.IrrigationData(uri[0]))
            elif uri[0] == "lighting":
                return json.dumps(self.weather.LightingData(uri[0]))
            else:
                raise cherrypy.HTTPError(404, "Wrong URL")


def sigterm_handler(signal, frame):
    webService.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
    settings = json.load(open("WeatherForecastSettings.json", "r"))

    ip_address, port = setREST(settings)

    print("Starting server...")

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }

    webService = WheaterService(settings)
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    while True:
        time.sleep(5)
