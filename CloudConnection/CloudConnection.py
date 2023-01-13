from pymongo import MongoClient
from pymongo import errors
import json
import time
import cherrypy
from GenericEndpoint import GenericEndpoint
import requests
from MyExceptions import *


class MongoConnection():
    def __init__(self):
        try:
            self.client = MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/test")
        except errors.AutoReconnect():
            print("Error connecting to the database")
        
        self.checkNewCompany()
    
    def insertDataBase(self, CompanyName):
        '''create a new database (company)
         Arguments:
         CompanyName: unique name of the company'''
        if CompanyName not in self.client.list_database_names():
            db = self.client[CompanyName]
            collection = db["CompanyData"]
            data = {"Company": CompanyName, "Database Creation Time": time.ctime()}
            collection.insert_one(data)
            print("Database created") 
        else:
            print("Database already exists")

    def insertField(self, CompanyName, CollectionName,data):
        '''create a collection for a field (dataset for a company)/update a collection\n
            Arguments:
            `CompanyName`: unique name of the company\n
            `CollectionName`: unique name of the collection\n
            `data`: data to be inserted in the collection\n'''
        if CompanyName in self.client.list_database_names():
            db = self.client[CompanyName]
            collection = db[CollectionName]
            data["_id"]=data.pop("bn")
            collection.insert_one(data)
        else:
            print("Company database is still being generated")
    def insertDataSensors(self, CompanyName, CollectionName,ID,data):
        '''insert data in a collection\n
            Parameters:
            CompanyName: unique name of the company
            CollectionName: unique name of the collection
            ID of the device
            data: data to be inserted in the collection'''
        if CompanyName in self.client.list_database_names():
            if CollectionName in self.client[CompanyName].list_collection_names():
                db = self.client[CompanyName]
                collection = db[CollectionName]
                data["_id"]=data.pop("bn")
                dict =list(collection.find())
                for i in range(len(data["e"])):
                    for j in range(len(dict[ID]["e"])):
                        if data["e"][i]["name"] == dict[ID]["e"][j]["name"]:
                            if type(dict[ID]["e"][j]["value"]) is not list:
                                dict[ID]["e"][j]["value"]=[dict[ID]["e"][j]["value"]]
                            if type(dict[ID]["e"][i]["timestamp"]) is not list:
                                dict[ID]["e"][i]["timestamp"]=[dict[ID]["e"][i]["timestamp"]]
                            dict[ID]["e"][j]["value"].extend([data["e"][i]["value"]])
                            dict[ID]["e"][j]["timestamp"].extend([data["e"][i]["timestamp"]])
                            collection.update_one({"_id":ID}, {"$set": dict[ID]})                                
            else:
                   self.insertField(CompanyName,CollectionName,data)
        else:
            print("Database does not exist, please create database first")
    
    #def insertDataService(self,CompanyName,CollectionName,data):       
    #da fare
                         
    def notify(self,topic, payload):
             '''get data on notification
            Parameters: \n
            `topic` -- string containing the topic of the new message\n
            `payload` -- string containing the payload of the new message\n'''
    
             list=topic.split("/")
             self.insertDataSensors(list[1],list[2],payload)
            
            #need how to get data from topic to right collection
            
        
    def checkNewCompany(self):
            '''check if a new company is added by making a GET request to the Resource Catalog'''
            while True:
                response = requests.get(self.ResourceCatalog_url + "/CompaniesName", self._SystemToken)
                list = json.loads(response)
                for i in list:
                    if i not in self.client.list_database_names():
                        self.insertDataBase(i)
                time.sleep(300)
            
                
    def GetAvg(self,CompanyName,CollectionName,measure):
        '''get the average of a measure\n
            Parameters:\n
            CompanyName: unique name of the company\n
            CollectionName: unique name of the collection\n
            measure: measure to be calculated\n'''
        if CompanyName in self.client.list_database_names():
            if CollectionName in self.client[CompanyName].list_collection_names():
                db = self.client[CompanyName]
                collection = db[CollectionName]
                dict =list(collection.find())
                lst=[]
                for i in range(len(dict)):
                    for j in range(len(dict[i]["e"])):
                        if dict[i]["e"][j]["name"] == measure:
                            lst.extend(dict[i]["e"][j]["value"])
                if len(lst)==0:
                    result={"result":f"No data available for {measure} in field {CollectionName} of company {CompanyName}"}
                else:
                    result={"Company":CompanyName,"Field":CollectionName,"Measure":measure,"Average":sum(lst)/len(lst),"Unit":dict[0]["e"][j]["unit"],"Timestamp":time.ctime()}
                return json.dumps(result)
            else:
                print("Collection does not exist")
        else:
            print("Database does not exist")
    def getAvgAll(self,CompanyName,measure):
        '''get the average of a measure for all the fields of a company\n
            Parameters:\n
            CompanyName: unique name of the company\n
            measure: measure to be calculated\n'''
        if CompanyName in self.client.list_database_names():
            db = self.client[CompanyName]
            lst=[]
            for i in db.list_collection_names():
                if i != "CompanyData":
                    result = self.GetAvg(CompanyName,i,measure)
                    if len(result)>1:
                        list.extend["Average"]
                        unit = result["Unit"]
            
            resultDict = {"Company":CompanyName,"Measure":measure,"Average":sum(lst)/len(lst),"Unit":unit,"Timestamp":time.ctime()}                       
            return json.dumps(resultDict)
        else:
            print("Database does not exist")
    def insertConsumptionData(self,CompanyName,CollectionName,ID):
        '''insert data coming from the consumption service\n
        Arguments:\n
        str: str coming from the consumption service\n'''
        # da sistemare con fede- capire come arrivano i dati non in csv
        db = self.client[CompanyName]
        collection = db[CollectionName]
        dict2={"consumption_value":2,"timestamp":time.ctime(),"unit":"kWh"}
        dict = list(collection.find()) 
        try:
            dict[ID]["consumption"].append(dict2)
            collection.update_one({"_id":ID}, {"$set": dict[ID]})
            return True
        except KeyError:
            print("its not an actuator")
            dict[ID]["consumption"]=[]   
            dict[ID]["consumption"].append(dict2)
            collection.update_one({"_id":ID}, {"$set": dict[ID]})
        except AttributeError:
            dict[ID]["consumption"]=[dict[ID]["consumption"]]
            dict[ID]["consumption"].append(dict2)
            collection.update_one({"_id":ID}, {"$set": dict[ID]})

        
    
    # def GetBotGrafici
class RESTApi(GenericEndpoint):
    exposed = True
    def __init__(self):
        super().__init__()
        self.mongo = MongoConnection()
        
    def GET(self, *uri, **params):
        '''GET method for the REST API\n
        Returns a JSON with the requested information\n
        Allowed URI:\n
        `/Avg` -- returns the average of the measures requested. The parameters are "CompanyName", "Field" and "measure"\n
        if `params["CompanyName"]` == "all" returns the average of all field of corresponding company\n'''
        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "avg" and params["CompanyName"] != "all":
                    return self.mongo.GetAvg(params["CompanyName"],params["Field"],params["measure"])
                elif len(uri) == 1 and uri[0] == "avg" and params["CompanyName"] == "all":                    
                    return self.mongo.getAvgAll(params["CompanyName"],params["measure"])
                else:
                    raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")
    # def POST(self,*uri,**params):
    #     '''POST method for the REST API\n
    #     Returns a JSON with the operation's status\n
    #     Allowed URI:\n
    #     `/insertConsumptionData` -- Insert the consumption data of the actuators of a field.\n 
    #     \tThe parameters are "CompanyName", "Field". \n
    #     '''
    #     try:
    #         if len(uri) > 0:
    #             if len(uri) == 1 and uri[0] == "insertConsumptionData":
    #                 #da capire come mi arrivano i dati
    #             else:
    #                 raise web_exception(404, "Resource not found.")
    #     except web_exception as e:
    #         raise cherrypy.HTTPError(e.code, e.message)
    #     except:
    #         raise cherrypy.HTTPError(500, "Internal Server Error")
                    
        
        
    
    
    
if __name__ == '__main__':
    conf =  {
            '/': {
                 'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                 'tools.sessions.on': True,
        }
    }
    webService = RESTApi()
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()     
