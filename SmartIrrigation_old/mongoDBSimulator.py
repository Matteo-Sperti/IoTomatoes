import cherrypy
import requests
from statistics import mean
import numpy.random as numpy
import json

#WEBSERVICE VELOCE SOLO PER TESTARE LA RICEZIONE DELLA MEDIA SMART IRRIGATION
class mongoDB():
    exposed=True
    def __init__(self):
        pass

    def GET(self,*uri,**params):
        if uri[0]=="increasing":
            currentValue=numpy.randint(55,70)
            previousValue=currentValue-5
        elif uri[0]=="decreasing":
            currentValue=numpy.randint(55,70)
            previousValue=currentValue-5
        elif uri[0]=="equal":
            currentValue=numpy.randint(55,70)
            previousValue=currentValue
        dictionary={
            "previousValue":previousValue,
            "currentValue":currentValue
        }
        return json.dumps(dictionary)
        

if __name__=="__main__":

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }
    mongo=mongoDB()
    cherrypy.tree.mount(mongo, "/", conf)
    cherrypy.engine.start()
    cherrypy.engine.block()