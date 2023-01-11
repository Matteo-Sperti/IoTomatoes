from pymongo import MongoClient
import json
import time
#from GenericEndpoint import GenericEndpoint
import requests


class MongoConnection():
    def __init__(self):
        self.client = MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/test")
        #super().__init__()
    
    def insertDataBase(self, CompanyName):
        '''create a new database (company)
         Arguments:
            CompanyName: unique name of the company'''
        if CompanyName in self.client.list_database_names():
            print("Database already exists")
        else:
            db = self.client[CompanyName]
            collection = db["CompanyData"]
            data = {"Company": CompanyName, "Database Creation Time": time.ctime()}
            collection.insert_one(data)
            print("Database created")
    def insertCollection(self, CompanyName, CollectionName,data):
        '''create a new collection (dataset for a company)/update a collection
            Arguments:
            CompanyName: unique name of the company
            CollectionName: unique name of the collection
            data: data to be inserted in the collection'''
        if CompanyName in self.client.list_database_names():
            db = self.client[CompanyName]
            update_flag = False
            if CollectionName in self.client[CompanyName].list_collection_names():
                update_flag = True
            db = self.client[CompanyName]
            collection = db[CollectionName]
            data["_id"]=data.pop("bn")
            collection.insert_one(data)
            if update_flag:
                print("Collection updated")
            else:
                print("Collection created")

        else:
            print("Database does not exist, please create database first")
    def sensorData(self, CompanyName, CollectionName,ID,data):
        '''insert data in a collection\n
            Parameters:
            CompanyName: unique name of the company
            CollectionName: unique name of the collection
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
                   print("Collection does not exist, please create collection first")
        else:
            print("Database does not exist, please create database first")
            
    def UpdateField(self,LocationOfTheValues,FieldToUpdate):
        '''update a field in a collection\n
            Parameters:\n
            LocationOfTheValues: location of the values to be updated\n
            FieldToUpdate: field to be updated'''
        #da fare
                         
    # def notify(self,topic, payload):
    #         '''get data on notification
    #         Parameters:
    #         notification: string containing the topic of the new message'''
    #         print(f"new message in topic: {topic}")
    #         list=topic.split("/")
    #         self.sensorData(list[1],list[2],payload)
            
            #need how to get data from topic to right collection
            
            

        
    #     '''get data when notify happens'''
    # def checkNewCompany(self,CatalogUrl):
    #         '''check if a new company is added by making a GET request to the Resource Catalog'''
    #         response = requests.get(self.ResourceCatalog_url + "/CompaniesName", self._SystemToken)
    #         list = json.loads(response)
    #         for i in list:
    #             if i not in self.client.list_database_names():
    #                 self.insertDataBase(i)
        
            
    #     '''check if a new company is added'''
    # def GetBotGrafici
    # def Getmedia
    '''da decidere se inserire o meno'''
if __name__ == '__main__':
    mongo = MongoConnection()
    #mongo.insertDataBase("Google")
    #print(mongo.client.list_database_names())
    #mongo.insertCollection("Google","Lighting",json.load(open("provajson.json","r")))
    mongo.sensorData("Google","Lighting",1,json.load(open("provajson.json","r")))
    company="Google"
   # print(list(mongo.client[company]["Lighting"].find()))
