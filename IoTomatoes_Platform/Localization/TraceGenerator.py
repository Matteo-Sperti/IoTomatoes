import json
import gpxpy
import folium
import cherrypy
import time
import signal
import requests
import imgkit
import base64
from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception
from iotomatoes_supportpackage.ItemInfo import setREST

class TraceGenerator(BaseService):
	def __init__(self,settings : dict,ResourceCatalogUrl : str,MongoDbUrl : str):

		self.create_url = settings["create_url"]
		self.view_url = settings["view_url"]
		self.pswd = settings["password"]
		self.MongoDbUrl = MongoDbUrl
		self.trackpoints = ""

		self.gpx_template   = """<?xml version="1.0" encoding="UTF-8"?>
		<gpx version="1.1" creator="Python GPX Generator">
			<trk>
			<trkseg>
				{trackpoints}
		</trkseg>
		</trk>
		</gpx>"""

	def TruckPosition(self,CompanyName):
		fileNameHtlm="mapPositions.html"
		fileNamePng="mapPositionsImage.png"
		params={"CompanyName":CompanyName}
		try:
			response=requests.get(self.MongoDbUrl+"/truckPosition",params)
			response.raise_for_status()
			dict_=response.json()
		except:
			raise web_exception(404,"Error getting data from the database")

		if dict_ != {}:
			map=folium.Map(location=[dict_[dict_.keys[0]]["latitude"],dict_[dict_.keys[0]]["longitude"]])
			for key in dict_.keys():
				folium.Marker([dict_[key]["latitude"],dict_[key]["longitude"]],popup="Truck "+key).add_to(map)
			map.save("mapPositions.html")
			imgkit.from_file(fileNameHtlm,fileNamePng)
			with open(fileNamePng, "rb") as image_file:
				encoded_string = base64.b64encode(image_file.read())
			return encoded_string
		else:
			raise web_exception(404,"No trucks found")


	def GenerateGPX(self,CompanyName,truckID):
		fileNameHtlm="mapTrace.html"
		fileNamePng="mapTraceImage.png"
		params={"CompanyName":CompanyName,"TruckID":truckID}
		try:
			response=requests.get(self.MongoDbUrl+"/truckTrace",params).json()
			response.raise_for_status()
			dict_=response.json()
		except:
			raise web_exception(404,"Error getting data from the database")
		if dict_!={}:
			lat=dict_["latitude"]
			lon=dict_["longitude"]
			for i in range(len(lat)):
					self.trackpoints += f"<trkpt lat='{lat[i]}' lon='{lon[i]}'></trkpt>\n"
			gpx_file = self.gpx_template.format(trackpoints=self.trackpoints)
	
			gpx = gpxpy.parse(gpx_file)
			first_point = gpx.tracks[0].segments[0].points[0]
			map = folium.Map(location=[first_point.latitude, first_point.longitude])
			# Add GPX track as a polyline on the map
			lat_lons = [(p.latitude, p.longitude) for p in gpx.tracks[0].segments[0].points]
			folium.PolyLine(lat_lons, color='red', weight=2.5, opacity=1).add_to(map)

			# Show map
			map.save(fileNameHtlm)
			imgkit.from_file(fileNameHtlm, fileNamePng)
			with open(fileNamePng, "rb") as image_file:
				encoded_string = base64.b64encode(image_file.read())
			return encoded_string
		else:
			raise web_exception(404,"No trucks found")


	   
class RESTConnector(BaseService):
	exposed = True
	def __init__(self,settings:dict):
		
		super().__init__(settings)
		if "MongoDB_ServiceName" in settings:
			self.mongoToCall = settings["MongoDB_ServiceName"]
		mongoDB_url = self.getOtherServiceURL(self.mongoToCall)
		self.traceGen = TraceGenerator(settings,self.ResourceCatalog_url, mongoDB_url)
	def GET(self,*uri,**params):
		try:
			if len(uri) > 0:
				if len(uri) == 1 and uri[0] == "trace":
					return self.traceGen.GenerateGPX(params["CompanyName"],params["TruckID"])
				if len(uri) == 1 and uri[0] == "position":
					return self.traceGen.TruckPosition(params["CompanyName"])
					
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
	

	while True:
		time.sleep(5)