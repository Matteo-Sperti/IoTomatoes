import requests
import json
import time
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

	def getData(self):
		'''gets the data from the weather API'''
		return self.makeRequest("WeatherInput.json","WeatherOutput.json") #makes the request and writes the output in the output file

if __name__ == '__main__':
	while True:
		weather = WeatherApp()
		weather.getData()
		time.sleep(1800)
		print(f"Weather data updated at {time.ctime()}")

	