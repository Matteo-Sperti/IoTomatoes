import json
import requests
import cherrypy
from typing import Iterable

def dic(a):
    lst = []
    for i in a.values():
        if isinstance(i, dict):
            lst.extend(dic(i))
        elif isinstance(i, list):
            lst.extend(i)
        else:
            lst.append(i)
    return lst


class WebPage:
    exposed = True
    def __init__(self):
        '''loads the keys from the input files required for picking the data from the Weather JSON file'''
        self.IrrigationDict = json.load(open("IrrigationInput.json","r"))
        self.LightingDict   = json.load(open("LightingInput.json","r"))
        self.Data = {}
        self.rawData = {}

   

    def GET(self,*uri,**params):
        '''handles the GET requests'''
        if len(uri) == 0:
            return "Welcome to the Weather Web Page"
        elif uri[0] == "Irrigation":
            #select the data taken from "WeatherOutput.json" based on the dictionary keys from "IrrigationInput.json" and create a new dictionary
            self.WeatherData = json.load(open("WeatherOutput.json","r"))
            #if the value  is present in IrrigationInput.json, then it is added to the new dictionary
            for key in self.IrrigationDict:
                if key in self.WeatherData:
                    self.rawData[key] = self.WeatherData[key]
            for key in list(self.rawData):
                for value in list(self.rawData[key]):
                    print(value)
                    if value in dic(self.IrrigationDict):
                        temp = self.rawData[key][value]
                        print(temp)
                        #self.Data.update(key,self.rawData[key])
                   


            return json.dumps(self.Data)


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