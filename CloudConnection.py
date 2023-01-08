from pymongo import MongoClient
import json
client = MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/test")
import time

class MongoConnection:
    def __init__(self):
        self.client = MongoClient("mongodb+srv://admin:admin@cluster0.lzvxrr9.mongodb.net/test")
        
    
    def insertDataBase(self, CompanyName):
        '''create a new database (company)'''
        if CompanyName in self.client.list_database_names():
            print("Database already exists")
        else:
            db = self.client[CompanyName]
            collection = db["CompanyData"]
            data = {"Company": CompanyName, "Database Creation Time": time.ctime()}
            collection.insert_one(data)
            print("Database created")
    def insertCollection(self, CompanyName, CollectionName,data):
        '''create a new collection (dataset for a company)'''
        if CompanyName in self.client.list_database_names():
            db = self.client[CompanyName]
            update_flag = False
            if CollectionName in self.client[CompanyName].list_collection_names():
                update_flag = True
            db = self.client[CompanyName]
            collection = db[CollectionName]
            collection.insert_one(data)
            if update_flag:
                print("Collection updated")
            else:
                print("Collection created")

        else:
            print("Database does not exist, please create database first")


if __name__ == '__main__':
    mongo = MongoConnection()
   # mongo.insertDataBase("Amazon")
    print(mongo.client.list_database_names())
    mongo.insertCollection("Google","Lighting",json.load(open("IrrigationOutput.json","r")))