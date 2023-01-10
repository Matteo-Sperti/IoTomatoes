import cherrypy
import requests
from statistics import mean
import numpy.random as numpy

#WEBSERVICE VELOCE SOLO PER TESTARE LA RICEZIONE DELLA MEDIA SMART IRRIGATION
class mongoDB():
    exposed=True
    def __init__(self):
        pass

    def GET(self,*uri,**params):
        lista=[25, 65, 48, 27, 84, 65, 46, 12, 23, 78]
        return f"{mean(lista)}"
        

if __name__=="__main__":

    conf={
        "/":{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on': True
            }
        }
    mongolo=mongoDB()
    cherrypy.tree.mount(mongolo, "/", conf)
    cherrypy.config.update({'server.socket_port': 8081})
    cherrypy.engine.start()
    cherrypy.engine.block()