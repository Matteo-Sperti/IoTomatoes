import json
import cherrypy
import requests
from matplotlib import pyplot as plt
from datetime import datetime
import signal
import base64

from iotomatoes_supportpackage import BaseService, web_exception, setREST


class DataVisualizer():
    def __init__(self, MongoDB_url: str, PointsPerGraph: int):
        """Constructor of the DataVisualizer class.

        Arguments:
        - `MongoDB_url (str)`: Url of the MongoDB service.
        - `PointsPerGraph (int)`: Number of points to be plotted in a graph.
        """
        self.MongoDB_url = MongoDB_url
        self.PointsPerGraph = PointsPerGraph

    def getGraphMeasure(self, CompanyName: str, Field: str, measure: str,
                        start: float, end: float):
        """Get the graph of a measure for a field of a company.

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `Field (str)`: Name of the field.
        - `measure (str)`: Name of the measure.
        - `start (float)`: Start date of the period.
        - `end (float)`: End date of the period.
        """

        fileName = "graphMeasure.png"
        print(f"Getting graph of {measure} for Field {Field} of {CompanyName} from {start} to {end}...")
        try:
            params = {
                "Field": Field,
                "measure": measure,
                "start_date": start,
                "end_date": end,
                "numPoints": self.PointsPerGraph
            }
            response = requests.get(
                f"{self.MongoDB_url}/{CompanyName}/vector", params=params)
            response.raise_for_status()
            res_dict = response.json()
        except:
            raise web_exception(
                404, "Error getting data from the database")
        else:
            xvalues = [datetime.fromtimestamp(
                x) for x in res_dict["t"]]
            yvalues = res_dict["v"]
            unit = res_dict["u"]

        if len(yvalues) > 0 and len(xvalues) > 0 and unit != "":
            plt.plot(xvalues, yvalues)
            plt.xlabel("Time")
            plt.ylabel(f"{measure} ({unit})")
            plt.title(
                f"Graph of {measure} for Field {Field} of {CompanyName}")
            plt.savefig(fileName)
            with open(fileName, "rb") as image2string:
                converted_string = base64.b64encode(image2string.read())

            out = {"img64": converted_string}
            return json.dumps(out)
        else:
            raise web_exception(404, "No data available")

    def getConsumptionGraph(self, CompanyName: str, start: float, end: float):
        """Construct histogram  of field consumption data a company.
        Multiple actuator can be monitored at the same time.

        Arguments:
        - `CompanyName (str)`: Name of the company.
        - `start (float)`: Start date of the period.
        - `end (float)`: End date of the period.
        """
        fileName = "graphConsumption.png"
        try:
            params = {"start_date": start, "end_date": end}
            response = requests.get(f"{self.MongoDB_url}/{CompanyName}/consumption",
                                    params=params)
            response.raise_for_status()
            dict_ = response.json()

            counts = dict_["Values"]
            bins = dict_["Fields"]
        except:
            raise web_exception(500, "Error getting data from the database")
        else:
            plt.bar(bins, counts)
            plt.xlabel("Fields")
            plt.ylabel(f"{dict_['Measure']} [{dict_['Unit']}]")
            for i in bins:
                plt.text(i, 0, f"Field {i}", color='blue', fontweight='bold',
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
            mongoToCall = settings["MongoDB_ServiceName"]
            mongoDB_url = self.getOtherServiceURL(mongoToCall)
            self.visualizer = DataVisualizer(
                mongoDB_url, settings["PointsPerGraph"])
        else:
            raise Exception("MongoDB service not found")

    def GET(self, *uri, **params):
        """GET method for the REST API

        Allowed URI:
        - `/<CompanyName>/measure`: returns the graph of the measures requested.
        The parameters are "Field" and "measure", "start_date", "end_date".
        if `params["Field"]` == "all" returns the average of all field of corresponding company.
        - `/<CompanyName>/consumption`: returns the graph of the consumption of the fields of the 
        company requested. The parameters are "start_date", "end_date".
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
