import requests
import json
import time
import cherrypy
from GenericEndpoint import GenericEndpoint
from MyExceptions import *


def validateJSON(jsonData):
	try:
		json.loads(jsonData)
	except ValueError as err:
		return False
	return True


class WeatherApp:
	'''handles the weather requests'''
	def __init__(self,settings):
		self.settings = settings
		self.url = self.settings["WeatherUrl"]
	def makeRequest(self,dictInput):
		'''handles an API request based on the JSON input file(forwards a getRequest to the weather API)'''
		response = requests.get(self.url, params=dictInput) #makes the request, the parameters are in the input file
		return response

	def IrrigationData(self):
		'''gets the data from the weather API for the irrigation service'''
		return self.makeRequest(self.settings["IrrigationDict"]) #makes the request 
	def LightingData(self):
		'''gets the data from the weather API for the lighting service'''
		response = self.makeRequest(self.settings["LightingDict"]) #makes the request
		listToBeConverted=(response["hourly"].pop("shortwave_radiation"))
		convertedList=[x/0.0079 for x in listToBeConverted] #converts the shortwave radiation to lux
		response["hourly"]["Illumination"]=convertedList
		listToBeConverted=response["daily"].pop("shortwave_radiation_sum")
		convertedList=[x/0.0079 for x in listToBeConverted] #converts the shortwave radiation to lux
		response["daily"]["Illumination_sum"]=convertedList
		response["hourly_units"]["Illumination"]="lux"
		response["hourly_units"].pop("shortwave_radiation")
		response["daily_units"]["Illumination_sum"]="lux"
		response["daily_units"].pop("shortwave_radiation_sum")
		return response #makes the 
	# def CustomData(self):
	# 	'''gets the data from the weather API for a  custom user request'''
	# 	return self.makeRequest(self.settings["CustomDict"]) for now deprecated



class WebPage(GenericEndpoint):
	exposed = True
	def __init__(self,settings):
		
		
		super().__init__(settings,True,False)
		self.weather= WeatherApp(self.settings,True,False)
	def GET(self,*uri,**params):
		if len(uri) != 0:
			if uri[0] == "Irrigation":
				return json.dumps(self.weather.IrrigationData())
			elif uri[0] == "Lighting":
				return json.dumps(self.weather.LightingData())
			elif uri[0] == "Custom":
				data = json.dumps(self.weather.CustomData())
				if data == "Null":
					raise cherrypy.HTTPError(400, "Wrong request")
				elif validateJSON(data) == False:
					raise cherrypy.HTTPError(400, "Wrong request")
				else:
					return json.dumps(data)
			
			else:
				raise cherrypy.HTTPError(404,"Wrong URL")
		else:
			raise cherrypy.HTTPError(404, "Please specify the service you want to use")



	

if __name__ == '__main__':
	
	settings=json.load(open("settings.json","r"))
	
	try:

		print("Starting server...")
		conf =  {
		 '/': {
			  'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
			  'tools.sessions.on': True,
		 	}
		 		}
		webService = WebPage(settings)
		cherrypy.tree.mount(webService, '/', conf)
		cherrypy.engine.start()
		cherrypy.engine.block() 
			
	

	except KeyboardInterrupt:
		cherrypy.engine.exit()
		cherrypy.server.stop()
