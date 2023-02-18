from pymongo import MongoClient, errors
import json
import time
import cherrypy
import requests
import signal
import pprint

from iotomatoes_supportpackage import BaseService, web_exception, setREST

MAX_TIME = 86400
MAX_TRUCK_TRACE = 1000


class MongoConnection():
    def __init__(self, ResourceCatalog_url: str, MongoDB_url: str, PlantDatabaseFileName: str):
        """Constructor of the MongoConnection class.

        Arguments:
        - `ResourceCatalog_url (str)`: Url of the ResourceCatalog service.
        - `MongoDB_url (str)`: Url of the MongoDB service.
        - `PlantDatabaseFileName (str)`: Name of the file containing the plant database.
        """
        self.ResourceCatalog_url = ResourceCatalog_url
        self.MongoDB_url = MongoDB_url
        self.PlantDatabaseFileName = PlantDatabaseFileName

        try:
            self.client = MongoClient(self.MongoDB_url)
        except errors.AutoReconnect:
            print("Error connecting to the database")
        else:
            self.loadPlantDatabase()
            self.checkNewCompany()

    def loadPlantDatabase(self):
        """Load the plant database in the MongoDB service."""

        PlantDatabase = json.load(open(self.PlantDatabaseFileName, "r"))

        if "PlantDatabase" in self.client.list_database_names():
            db = self.client["PlantDatabase"]
            collection = db["PlantData"]
            collection.drop()
            print("PlantDatabase dropped")

        db = self.client["PlantDatabase"]
        collection = db["PlantData"]
        for i in PlantDatabase.keys():
            dictionary = PlantDatabase[i]
            dictionary["PlantName"] = i
            collection.insert_one(dictionary)
        print("PlantDatabase loaded")

    def insertDataBase(self, CompanyName: str):
        """Create a database for a company.

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        """
        if CompanyName in self.client.list_database_names():
            print("Database already exists")
        else:
            try:
                db = self.client[CompanyName]
                db.create_collection("0")

                response = requests.get(
                    f"{self.ResourceCatalog_url}/{CompanyName}/fields")
                response.raise_for_status()
                list_fields = response.json()
                for j in list_fields:
                    self.insertField(CompanyName, str(j["fieldNumber"]))

                print("Database created")
            except:
                print("Error in creating the database")

    def deleteDatabase(self, CompanyName: str):
        """Delete a database (company).

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        """
        if CompanyName not in self.client.list_database_names():
            print("Database not found")
        else:
            try:
                self.client.drop_database(CompanyName)
                print("Database deleted")
            except errors.OperationFailure:
                print("Error in deleting the database")

    def insertField(self, CompanyName: str, CollectionName: str):
        """Create/update a collection (a.k.a a field) in the database of a company.

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        - `CollectionName (str)`: unique name of the collection(a.k.a. field).
        """
        self.insertDataBase(CompanyName)
        db = self.client[CompanyName]
        if CollectionName in db.list_collection_names():
            print("Collection already exists")
        else:
            db.create_collection(CollectionName)

    def insertData(self, ID: int, data: dict):
        """Insert data in a collection.

        Arguments:
        - `data (dict)`: data to be inserted in the collection.
        """
        data["_id"] = ID

        CompanyName = data.pop("cn")
        fieldNumber = str(data.pop("fieldNumber"))

        if CompanyName not in self.client.list_database_names():
            print("Company not found, failed to insert data")
            return
        if fieldNumber not in self.client[CompanyName].list_collection_names():
            print("Field not found, failed to insert data")
            return

        collection = self.client[CompanyName][fieldNumber]

        dict_ = collection.find_one({"_id": ID})

        if dict_ == None:
            new_data = {
                "_id": ID,
                "e": []
            }
            collection.insert_one(new_data)
        elif "e" not in dict_:
            collection.update_one({"_id": ID}, {"$set": {"e": []}})

        if "e" in data:
            if isinstance(data["e"], list):
                collection.update_one(
                    {"_id": ID}, {"$push": {"e": {"$each": data["e"]}}})
            else:
                collection.update_one({"_id": ID}, {"$push": {"e": data["e"]}})
        else:
            print("No data to insert")

    def refresh(self):
        """Refresh the database."""
        self.checkNewCompany()
        self.autoDeleteOldData()

    def autoDeleteOldData(self):
        """Delete old data from the database."""
        current_time = time.time()
        for i in self.client.list_database_names():
            if i != "PlantDatabase" and i != "admin" and i != "local":
                db = self.client[i]
                for j in db.list_collection_names():
                    collection = db[j]
                    collection.update_many(
                        {}, {"$pull": {"e": {"t": {"$lt": current_time - MAX_TIME}}}})

    def checkNewCompany(self):
        """Check if a new company has been added to the ResourceCatalog or if a company has been deleted."""
        try:
            response = requests.get(
                self.ResourceCatalog_url + "/companies/names")
            response.raise_for_status()
            list_names = response.json()

            for i in list_names:
                if i not in list(self.client.list_databases()):
                    self.insertDataBase(i)

            for j in self.client.list_database_names():
                if j not in list_names and (j != "PlantDatabase" and j != "admin" and j != "local"):
                    print(j)
                    self.deleteDatabase(j)
        except:
            print("Error in Database")

    def GetAvg(self, CompanyName: str, CollectionName: str, measure: str,
               start: float, end: float):
        """Get the average of a measure in a period of time.

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        - `CollectionName (str)`: name of the collection.
        - `measure (str)`: name of the measure.
        - `start (float)`: start date of the period.
        - `end (float)`: end date of the period.
        """

        if CompanyName not in self.client.list_database_names():
            raise web_exception(404, "Company not found")

        if CollectionName not in self.client[CompanyName].list_collection_names():
            raise web_exception(404, "Field not found")

        collection = self.client[CompanyName][CollectionName]

        res = collection.aggregate([
            {"$match": {"e.n": measure, "e.t": {"$gte": start, "$lte": end}}},
            {"$unwind": "$e"},
            {"$match": {"e.n": measure, "e.t": {"$gte": start, "$lte": end}}},
            {"$group": {
                "_id": None,
                "Average": {"$avg": "$e.v"},
                "Unit": {"$first": "$e.u"},
                "Measure": {"$first": "$e.n"},
                "StartTime": {"$min": "$e.t"},
                "EndTime": {"$max": "$e.t"}
            }},
            {"$project": {
                "_id": 0,
                "Average": 1,
                "Unit": 1,
                "Measure": 1,
                "StartTime": 1,
                "EndTime": 1
            }}
        ])
        res_list = list(res)
        if res == None or len(res_list) == 0:
            raise web_exception(404, "No data found")

        res_info = res_list[0]
        result = {
            "Company": CompanyName,
            "Field": CollectionName
        }
        result.update(res_info)
        return json.dumps(result)

    def getAvgAll(self, CompanyName: str, measure: str, start: float, end: float):
        """Get the average of a measure in a period of time for all the fields of a company.

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        - `measure (str)`: name of the measure.
        - `start (float)`: start date of the period.
        - `end (float)`: end date of the period.
        """
        if CompanyName not in self.client.list_database_names():
            raise web_exception(404, "Company not found")
        else:
            db = self.client[CompanyName]
            lst = []
            unit = ""
            for i in db.list_collection_names():
                try:
                    res = self.GetAvg(CompanyName, i, measure, start, end)
                except:
                    pass
                else:
                    result = json.loads(res)
                    lst.append(result["Average"])
                    unit = result["Unit"]

            if len(lst) == 0:
                raise web_exception(404, "No data found")

            resultDict = {
                "Company": CompanyName,
                "Measure": measure,
                "Average": sum(lst)/len(lst),
                "Unit": unit,
                "Timeperiod": [start, end]
            }
            return json.dumps(resultDict)

    def getConsumptionData(self, CompanyName: str, start: float, end: float):
        """Get the consumption data of a company

        Arguments:
        - `CompanyName (str)`: unique name of the company
        - `start (float)`: start date of the period
        - `end (float)`: end date of the period
        """
        if CompanyName not in self.client.list_database_names():
            raise web_exception(404, "Company not found")

        if self.client[CompanyName].list_collection_names() == []:
            raise web_exception(404, "No collection found")

        consumption = []
        fields = []
        unit = ""
        resultDict = {}

        for CollectionName in self.client[CompanyName].list_collection_names():
            collection = self.client[CompanyName][CollectionName]
            res = collection.aggregate([
                {"$match": {"e.n": "consumption", "e.t": {"$gte": start, "$lte": end}}},
                {"$unwind": "$e"},
                {"$match": {"e.n": "consumption", "e.t": {"$gte": start, "$lte": end}}},
                {"$group": {
                    "_id": None,
                    "total": {"$sum": "$e.v"},
                    "unit": {"$first": "$e.u"},
                }},
                {"$project": {
                    "_id": 0,
                    "total": 1,
                    "unit": 1,
                }}
            ])
            res_list = list(res)
            if res_list != []:
                res_info = res_list[0]
                consumption.append(res_info["total"])
                fields.append(CollectionName)
                if unit == "":
                    unit = res_info["unit"]

        if len(consumption) == 0:
            raise web_exception(404, "Measure not found")
        else:
            resultDict = {
                "Company": CompanyName,
                "Fields": fields,
                "Measure": "Consumption",
                "Values": consumption,
                "Unit": unit,
                "Time Period": [start, end],
            }
            return json.dumps(resultDict)

    def GetMeasureVector(self, CompanyName: str, **kwargs):
        """Get the average of a measure in a period of time.

        Arguments:
        - `CompanyName (str)`: unique name of the company.
        - `CollectionName (str)`: name of the collection.
        - `measure (str)`: name of the measure.
        - `start (float)`: start date of the period.
        - `end (float)`: end date of the period.
        """
        if "Field" not in kwargs:
            raise web_exception(400, "Missing CollectionName")
        else:
            CollectionName = kwargs["Field"]
        
        if "measure" not in kwargs:
            raise web_exception(400, "Missing measure")
        else:
            measure = kwargs["measure"]
        
        if "start_date" not in kwargs:
            raise web_exception(400, "Missing start")
        else:
            start = float(kwargs["start_date"])
        
        if "end_date" not in kwargs:
            raise web_exception(400, "Missing end")
        else:
            end = float(kwargs["end_date"])

        if "numPoints" in kwargs:
            numPoints = int(kwargs["numPoints"])
        else:
            numPoints = 100
    
        if CompanyName not in self.client.list_database_names():
            raise web_exception(404, "Company not found")

        if CollectionName not in self.client[CompanyName].list_collection_names():
            raise web_exception(404, "Field not found")

        collection = self.client[CompanyName][CollectionName]

        res = collection.aggregate([
            {"$match": {"e.n": measure, "e.t": {"$gte": start, "$lte": end}}},
            {"$unwind": "$e"},
            {"$match": {"e.n": measure, "e.t": {"$gte": start, "$lte": end}}},
            {"$sort": {"e.t": -1}},
            {"$project": {
                "_id": 0,
                "v": "$e.v",
                "u": "$e.u",
                "t": "$e.t"
            }},
            {
                "$bucketAuto": {
                    "groupBy": "$t",
                    "buckets": numPoints,
                    "output": {
                        "v": {"$avg": "$v"},
                        "u": {"$first": "$u"},
                        "t": {"$avg": "$t"}
                    }
                }},
            {"$group": {
                "_id": None,
                "v": {"$push": "$v"},
                "t": {"$push": "$t"},
                "u": {"$first": "$u"}
            }},
            {"$project": {
                "_id": 0,
                "v": 1,
                "t": 1,
                "u": 1
            }}
        ])

        res_list = list(res)
        if res == None or len(res_list) == 0:
            raise web_exception(404, "No data found")

        res_info = res_list[0]
        result = {
            "Company": CompanyName,
            "Field": CollectionName
        }
        result.update(res_info)
        return json.dumps(result)

    def getTruckTrace(self, CompanyName: str, TruckID: int):
        """Get the truck trace informations

        Arguments:
        - `CompanyName (str)`: name of the company
        - `TruckID (int)`: id of the truck
        """

        collection = self.client[CompanyName]["0"]

        res = collection.aggregate([
            {"$match": {"_id": TruckID, "e.n": "position"}},
            {"$unwind": "$e"},
            {"$match": {"e.n": "position"}},
            {"$sort": {"e.t": -1}},
            {"$limit": MAX_TRUCK_TRACE},
            {"$project": {
                "_id": 0,
                "latitude": "$e.v.latitude",
                "longitude": "$e.v.longitude",
                "timestamps": "$e.t"
            }},
            {"$group": {
                "_id": None,
                "latitude": {"$push": "$latitude"},
                "longitude": {"$push": "$longitude"},
                "timestamps": {"$push": "$timestamps"}
            }},
            {"$project": {
                "_id": 0,
                "latitude": "$latitude",
                "longitude": "$longitude",
                "timestamps": "$timestamps"
            }}
        ])

        try:
            res_info = list(res)[0]
            return json.dumps(res_info)
        except:
            raise web_exception(404, "Truck not found")

    def getTrucksPosition(self, CompanyName: str):
        """Get the trucks position informations

        Arguments:
        - `CompanyName (str)`: name of the company
        """
        collection = self.client[CompanyName]["0"]

        res = collection.aggregate([
            {"$match": {"e.n": "position"}},
            {"$unwind": "$e"},
            {"$match": {"e.n": "position"}},
            {"$group": {
                "_id": "$_id",
                "e": {"$last": "$e"},
            }},
            {"$group": {
                "_id": None,
                "docs": {
                    "$push": {
                        "id": "$_id",
                        "lat": "$e.v.latitude",
                        "lon": "$e.v.longitude",
                        "u": "$e.u",
                        "t": "$e.t"
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "data": {
                    "$arrayToObject": {
                        "$map": {
                            "input": "$docs",
                            "in": {
                                "k": {"$toString": "$$this.id"},
                                "v": {
                                    "latitude": "$$this.lat",
                                    "longitude": "$$this.lon",
                                    "u": "$$this.u",
                                    "t": "$$this.t"
                                }
                            }
                        }
                    }
                }
            }}
        ])
        res_list = list(res)

        try:
            return json.dumps(res_list[0]["data"])
        except:
            raise web_exception(404, "No data found")

    def getPlant(self, PlantName: str):
        """Get the plant informations

        Arguments:
        - `PlantName (str)`: name of the plant
        """
        db = self.client["PlantDatabase"]
        collection = db["PlantData"]
        item = collection.find_one({"PlantName": PlantName})

        def exctractPlantInfo(dict_: dict):
            """Extract the plant informations from the dictionary"""
            plantInfo = {}
            plantInfo["lightLimit"] = dict_["lightLimit"]
            plantInfo["soilMoistureLimit"] = dict_["soilMoistureLimit"]
            plantInfo["precipitationLimit"] = dict_["precipitationLimit"]
            return plantInfo

        if item != None:
            return json.dumps(exctractPlantInfo(item))
        else:
            default = collection.find_one({"PlantName": "default"})
            if default == None:
                raise web_exception(500, "Default values not found")
            return json.dumps(exctractPlantInfo(default))


class RESTConnector(BaseService):
    exposed = True

    def __init__(self, settings: dict):
        """Constructor of the RESTConnector class"""
        super().__init__(settings)
        self.mongo = MongoConnection(
            self.ResourceCatalog_url, settings["MongoDB_Url"], settings["PlantDatabaseName"])

    def notify(self, topic, payload):
        """Notify the observer that a new data has arrived.

        Arguments:
        - `topic (str)`: topic of the message.
        - `payload (str)`: payload of the message.
        """

        listTopic = topic.split("/")
        try:
            # Company/Field/ID/measure
            if len(listTopic) >= 4 and isInteger(listTopic[1]) and isInteger(listTopic[2]):
                self.mongo.insertData(int(listTopic[2]), payload)
        except:
            pass

    def GET(self, *uri, **params):
        """GET method for the REST API

        Allowed URI:
        - `/<CompanyName>/avg` : get the average of a measure in a field of a company.
        The parameters are: `Field`, `measure`, `start_date`, `end_date`. 
        If `Field` is `all`, the average of all the fields is returned.
        - `/<CompanyName>/vector` : get the last measure of a field of a company.
        The parameters are: `Field`, `measure`, `start_date`, `end_date`. 
        - `/<CompanyName>/truckTrace` : get the trace of a truck.
        The parameter is: `TruckID`.
        - `/<CompanyName>/trucksPosition` : get the position of all the trucks.
        - `/<CompanyName>/consumption` : get the consumption data of a company.
        The parameters are: `start_date`, `end_date`.
        - '/plant' : get the plant informations. The parameter is: `PlantName`.
        """

        try:
            if len(uri) == 2 and uri[1] == "avg" and params["Field"] != "all":
                return self.mongo.GetAvg(uri[0], params["Field"], params["measure"],
                                         float(params["start_date"]), float(params["end_date"]))
            elif len(uri) == 2 and uri[1] == "avg" and params["Field"] == "all":
                return self.mongo.getAvgAll(uri[0], params["measure"],
                                            float(params["start_date"]), float(params["end_date"]))
            elif len(uri) == 2 and uri[1] == "vector":
                return self.mongo.GetMeasureVector(uri[0], **params)
            elif len(uri) == 3 and uri[2] == "trace":
                return self.mongo.getTruckTrace(uri[0], int(uri[1]))
            elif len(uri) == 2 and uri[1] == "trucksPosition":
                return self.mongo.getTrucksPosition(uri[0])
            elif len(uri) == 2 and uri[1] == "consumption":
                return self.mongo.getConsumptionData(uri[0], float(params["start_date"]), float(params["end_date"]))
            elif len(uri) == 1 and uri[0] == "plant":
                return self.mongo.getPlant(params["PlantName"])
            else:
                raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")


def isInteger(string: str):
    """Check if the string is an integer"""
    try:
        int(string)
        return True
    except ValueError:
        return False


def sigterm_handler(signal, frame):
    """Handler for the SIGTERM signal"""
    global run
    global WebService

    run = False
    WebService.mongo.client.close()
    WebService.stop()
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    settings = json.load(open("ConnectorSettings.json"))

    ip_address, port = setREST(settings)

    WebService = RESTConnector(settings)
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(WebService, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    run = True
    while run:
        WebService.mongo.refresh()
        time.sleep(30)
