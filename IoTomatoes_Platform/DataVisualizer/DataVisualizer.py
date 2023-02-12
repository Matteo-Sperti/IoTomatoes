import json
import cherrypy
import requests
from matplotlib import pyplot as plt
from datetime import datetime
import signal
import base64
import imgkit

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception
from iotomatoes_supportpackage.ItemInfo import setREST

class DataVisualizer():
	def __init__(self, ResourceCatalog_url : str, MongoDB_url : str, PointsPerGraph : int):
		self.ResourceCatalog_url = ResourceCatalog_url
		self.MongoDB_url = MongoDB_url
		self.PointsPerGraph = PointsPerGraph



	def getGraphMeasure(self,CompanyName,CollectionName,measure,start,end):
		'''get the graph of a measure for a field of a company\n
		Parameters:\n
		`CompanyName` -- unique name of the company\n
		`collectionName` -- field of the company\n
		`Measure` -- measure to be calculated\n
		`Start` -- start date of the period\n
		`end` -- end date of the period\n'''
		fileName="graphMeasure.png"
		lst=[]
		try:
			response=requests.get(self.MongoDB_url+"/graph",params={"CompanyName":CompanyName,"CollectionName":CollectionName,"measure":measure,"start_date":start,"end_date":end})
			response.raise_for_status()
			dataDict=response.json()
		except requests.exceptions.ConnectionError:
			raise web_exception(404,"Error getting data from the database")
		timestamps= dataDict[max(dataDict, key=lambda x: len(dataDict[x]["timestamps"]))]["timestamps"]
		unit=dataDict[dataDict.keys()[0]]["unit"]
		if len(timestamps)/self.PointsPerGraph > 1:
			step = int(len(timestamps)/self.PointsPerGraph)
			timestamps = timestamps[::step]
			for i in range(len(timestamps)):
				try:
					response=requests.get(self.MongoDB_url+"/average",params={"CompanyName":CompanyName,"CollectionName":CollectionName,"neasure":measure,"start_date":0,"end_date":timestamps[i+1]})
					response.raise_for_status()
					avg=response.json()
				except:
					raise web_exception(404,"Error getting data from the database")
				if avg != None and avg != False:
					lst.append(avg["Average"])
				timestamps[i]=datetime.fromtimestamp(timestamps[i])

			#plot graph
			plt.plot(timestamps,lst)
			plt.xlabel("Time")
			plt.ylabel(measure+" ("+unit+")")
			plt.title("Graph of "+measure+" for "+CollectionName+" of "+CompanyName)
			plt.savefig(fileName)
			with open(fileName, "rb") as image2string:
				converted_string = base64.b64encode(image2string.read())
			return(converted_string)
		else:
			raise web_exception(404,"Not enough data to plot the graph")
			
	def getConsumptionGraph(self,CompanyName,start,end):
			'''get histogram  of field consumption data a company\n
			Multiple actuator can be monitored at the same time\n
			Parameters:\n
			`CompanyName` -- unique name of the company\n
			`Start` -- start date of the period\n
			`end` -- end date of the period\n'''
			fileName="graphConsumption.png"
			try:
				response=requests.get(self.MongoDB_url+"/consumption",params={"CompanyName":CompanyName,"start_date":start,"end_date":end})
				response.raise_for_status()
				dict_=response.json()
			except:
				raise web_exception(404,"Error getting data from the database")
				
			if dict_ != None and dict_ != False:
				counts=[]
				bins=[]
				for i in dict_.keys():
        
					counts.append(dict_[i]["lvalues"])
					bins.append(i)
     
				plt.bar(bins,counts)
				plt.xlabel("Fields")
				plt.ylabel("Consumption (kWh)")
				for i,v in enumerate(counts):
					plt.text(i,v,str(v),color='blue',fontweight='bold',horizontalalignment='center',verticalalignment='bottom')
				plt.show()
				plt.title("Graph of consumption data")
				plt.savefig(fileName)
				with open(fileName, "rb") as image2string:
					converted_string = base64.b64encode(image2string.read())

				return(converted_string)
			else:
				return web_exception(404,"No consumption data available")
 
class RESTConnector(BaseService):
	exposed = True
	def __init__(self,settings:dict):
		
		super().__init__(settings)
		if "MongoDB_ServiceName" in settings:
			self.mongoToCall = settings["MongoDB_ServiceName"]
		mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
		self.visualizer = DataVisualizer(self.ResourceCatalog_url, mongoDB_url,settings["PointsPerGraph"])
		
	def GET(self, *uri, **params):
		"""GET method for the REST API\n
		Returns a JSON with the requested information\n
		Allowed URI:\n
		`/Avg`: returns the average of the measures requested.\n 
		The parameters are "CompanyName", "Field" and "measure", "starting date", "end date"\n
		if `params["Field"]` == "all" returns the average of all field of corresponding company\n"""
		try:
			if len(uri) > 0:
				if len(uri) == 1 and uri[0] == "measure" :
					return self.visualizer.getGraphMeasure(params["CompanyName"],params["Field"],params["measure"],params["start_date"],params["end_date"])
				elif len(uri) == 1 and uri[0] == "consumption":                    
					return self.visualizer.getConsumptionGraph(params["CompanyName"],params["start_date"],params["end_date"])
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
	settings = json.load(open("DataVisualizerSettings.json"))

	ip_address, port = setREST(settings)

	WebService = RESTConnector(settings)
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