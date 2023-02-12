import json
import cherrypy
import requests
from matplotlib import pyplot as plt
from datetime import datetime
import signal
import base64

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception
from iotomatoes_supportpackage.ItemInfo import setREST


class DataVisualizer():
    def __init__(self, MongoDB_url: str, PointsPerGraph: int):
        """Constructor of the DataVisualizer class.

        Arguments:
        - `MongoDB_url (str)`: Url of the MongoDB service.
        - `PointsPerGraph (int)`: Number of points to be plotted in a graph.
        """
        self.MongoDB_url = MongoDB_url
        self.PointsPerGraph = PointsPerGraph

    def getGraphMeasure(self, CompanyName: str, CollectionName: str, measure: str,
                        start: str, end: str):
        """Get the graph of a measure for a field of a company.

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `CollectionName (str)`: Name of the field.
        - `measure (str)`: Name of the measure.
        - `start (str)`: Start date of the period.
        - `end (str)`: End date of the period.
        """

        fileName = "graphMeasure.png"
        lst = []
        try:
            params = {
                "CompanyName": CompanyName,
                "CollectionName": CollectionName,
                "measure": measure,
                "start_date": start,
                "end_date": end
            }
            response = requests.get(self.MongoDB_url+"/graph", params=params)
            response.raise_for_status()
            dataDict = response.json()
        except:
            raise web_exception(404, "Error getting data from the database")

        timestamps = dataDict[max(dataDict, key=lambda x: len(
            dataDict[x]["timestamps"]))]["timestamps"]
        unit = dataDict[dataDict.keys()[0]]["unit"]
        if len(timestamps)/self.PointsPerGraph > 1:
            step = int(len(timestamps)/self.PointsPerGraph)
            timestamps = timestamps[::step]
            for i in range(len(timestamps)):
                try:
                    params = {
                        "CompanyName": CompanyName,
                        "CollectionName": CollectionName,
                        "measure": measure,
                        "start_date": start,
                        "end_date": end,
                        "timestamp": timestamps[i]
                    }
                    response = requests.get(
                        self.MongoDB_url+"/average", params=params)
                    response.raise_for_status()
                    avg = response.json()
                except:
                    raise web_exception(
                        404, "Error getting data from the database")

                if avg != None and avg != False:
                    lst.append(avg["Average"])
                timestamps[i] = datetime.fromtimestamp(timestamps[i])

            # plot graph
            plt.plot(timestamps, lst)
            plt.xlabel("Time")
            plt.ylabel(f"{measure} ({unit})")
            plt.title(
                f"Graph of {measure} for {CollectionName} of {CompanyName}")
            plt.savefig(fileName)
            with open(fileName, "rb") as image2string:
                converted_string = base64.b64encode(image2string.read())
            return (converted_string)
        else:
            raise web_exception(404, "Not enough data to plot the graph")

    def getConsumptionGraph(self, CompanyName: str, start: str, end: str):
        """Construct histogram  of field consumption data a company.
        Multiple actuator can be monitored at the same time.

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `start (str)`: Start date of the period.
        - `end (str)`: End date of the period.
        """
        fileName = "graphConsumption.png"
        try:
            params = {"CompanyName": CompanyName,
                      "start_date": start, "end_date": end}
            response = requests.get(
                self.MongoDB_url+"/consumption", params=params)
            response.raise_for_status()
            dict_ = response.json()
        except:
            raise web_exception(404, "Error getting data from the database")

        if dict_ == None or dict_ == False:
            raise web_exception(404, "No consumption data available")
        else:
            counts = []
            bins = []
            for i in dict_.keys():
                counts.append(dict_[i]["lvalues"])
                bins.append(i)

            plt.bar(bins, counts)
            plt.xlabel("Fields")
            plt.ylabel("Consumption (kWh)")
            for i, v in enumerate(counts):
                plt.text(i, v, str(v), color='blue', fontweight='bold',
                         horizontalalignment='center', verticalalignment='bottom')
            plt.show()
            plt.title("Graph of consumption data")
            plt.savefig(fileName)
            with open(fileName, "rb") as image2string:
                converted_string = base64.b64encode(image2string.read())

            out = {"img64": converted_string}
            return json.dumps(out)


class WebService(BaseService):
    exposed = True

    def __init__(self, settings: dict):
        """Constructor of the WebService class. 
        It calls the constructor of the BaseService class and initializes the DataVisualizer 
        class given as parameter the service `settings`."""

        super().__init__(settings)
        if "MongoDB_ServiceName" in settings:
            self.mongoToCall = settings["MongoDB_ServiceName"]
        mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
        self.visualizer = DataVisualizer(
            mongoDB_url, settings["PointsPerGraph"])

    def GET(self, *uri, **params):
        """GET method for the REST API

        Allowed URI:
        - `<CompanyName>/measure`: returns the graph of the measures requested.
        The parameters are "Field" and "measure", "starting date", "end date".
        if `params["Field"]` == "all" returns the average of all field of corresponding company.
        - `<CompanyName>/consumption`: returns the graph of the consumption of the fields of the 
        company requested. The parameters are "starting date", "end date".
        """
        try:
            if len(uri) == 2 and uri[1] == "measure":
                return self.visualizer.getGraphMeasure(uri[0], params["Field"], params["measure"],
                                                       params["start_date"], params["end_date"])
            elif len(uri) == 2 and uri[1] == "consumption":
                return self.visualizer.getConsumptionGraph(uri[0], params["start_date"], params["end_date"])
            else:
                raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")


def sigterm_handler(signal, frame):
    Service.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    settings = json.load(open("DataVisualizerSettings.json"))

    ip_address, port = setREST(settings)

    Service = WebService(settings)
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(Service, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()
