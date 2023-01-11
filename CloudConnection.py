from pymongo import MongoClient
from pymongo import errors
import json
import time
#from GenericEndpoint import GenericEndpoint
import requests

class MongoConnection():
    def __init__(self):
        try:
            self.client = MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/test")
        except errors.AutoReconnect():
            print("Error connecting to the database")
        #super().__init__()
        #self.checkNewCompany()
    
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
                            temp=dict[ID]["e"][j]["value"].extend([data["e"][i]["value"]])
                            collection.update_one({"_id":ID}, {"$set": dict[ID]})
            else:
                   self.insertField(CompanyName,CollectionName,data)
        else:
            print("Database does not exist, please create database first")
    
    def insertDataService(self,CompanyName,CollectionName,data):       
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
            
                

    # def GetBotGrafici
    # def Getmedia
    '''da decidere se inserire o meno'''
if __name__ == '__main__':
    mongo = MongoConnection()
    #mongo.insertDataBase("Google")
    #print(mongo.client.list_database_names())
    #mongo.insertCollection("Google","Lighting",json.load(open("provajson.json","r")))
    #mongo.insertDataSensors("Google","Lighting",2,json.load(open("provajson.json","r")))
    company="Google"
    mongo.insertDataBase("Google")
   # print(list(mongo.client[company]["Lighting"].find()))
