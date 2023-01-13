import requests
import json
import time
import cherrypy


def validateJSON(jsonData):
    try:
        json.loads(jsonData)
    except ValueError as err:
        return False
    return True


class WeatherApp:
	'''handles the weather requests'''
	def __init__(self):
		self.url= "https://api.open-meteo.com/v1/forecast"
	def makeRequest(self,fileInput,fileOutput):
		'''handles an API request based on the JSON input file(forwards a getRequest to the weather API)'''
		dict = json.load(open(fileInput,"r")) #loads the input file
		response = requests.get(self.url, params=dict) #makes the request, the parameters are in the input file
		json.dump(response.json(),open(fileOutput,"w")) #writes the output in the output file
		return response.json()

	def IrrigationData(self):
		'''gets the data from the weather API for the irrigation service'''
		return self.makeRequest("IrrigationInput.json","IrrigationOutput.json") #makes the request and writes the output in the output file
	def LightingData(self):
		'''gets the data from the weather API for the lighting service'''
		return self.makeRequest("LightingInput.json","LightingOutput.json") #makes the request and writes the output in the output file
	def CustomData(self):
		'''gets the data from the weather API for a  custom user request'''
		return self.makeRequest("CustomInput.json","CustomOutput.json") #makes the request and writes the output in the output file



class WebPage(object):
	exposed = True
	def GET(self,*uri,**params):
		if len(uri) != 0:
			if uri[0] == "Irrigation":
				weather = WeatherApp()
				return json.dumps(weather.IrrigationData())
			elif uri[0] == "Lighting":
				weather = WeatherApp()
				return json.dumps(weather.LightingData())
			elif uri[0] == "Custom":
				weather = WeatherApp()
				data = json.dumps(weather.CustomData())
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
	conf =  {
			'/': {
				 'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
				 'tools.sessions.on': True,
		}
	}
	webService = WebPage()
	cherrypy.tree.mount(webService, '/', conf)
	cherrypy.engine.start()
	cherrypy.engine.block()     