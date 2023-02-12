from pymongo import MongoClient
from pymongo import errors
import json
import time
import cherrypy
import requests
import signal

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception
from iotomatoes_supportpackage.ItemInfo import setREST


class MongoConnection():
    def __init__(self, ResourceCatalog_url: str, MongoDB_url: str, PlantDatabaseFileName: str):
        self.ResourceCatalog_url = ResourceCatalog_url
        self.MongoDB_url = MongoDB_url
        self.PlantDatabaseFileName = PlantDatabaseFileName

        try:
            self.client = MongoClient(self.MongoDB_url)
        except errors.AutoReconnect:
            print("Error connecting to the database")
        else:
            self.checkNewCompany()
            self.loadPlantDatabase(self.PlantDatabaseFileName)

    def loadPlantDatabase(self, FileName):
        '''load the plant database in the MongoDB'''
        PlantDatabase = json.load(open(FileName))

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

    def insertDataBase(self, CompanyName):
        '''create a new database (company)
         Arguments:
         CompanyName: unique name of the company'''
        if CompanyName not in self.client.list_database_names():
            try:
                db = self.client[CompanyName]
                collection = db["CompanyData"]
                data = {"Company": CompanyName,
                        "Database Creation Time": time.ctime()}
                collection.insert_one(data)
                print("Database created")
            except errors.InvalidName:
                print("Error in creating the database")
        else:
            print("Database already exists")

    def deleteDatabase(self, CompanyName):
        '''delete a database (company)
         Arguments:
         CompanyName: unique name of the company'''
        if CompanyName in self.client.list_database_names():
            try:
                self.client.drop_database(CompanyName)
                print("Database deleted")
            except errors.OperationFailure:
                raise web_exception(500, "Error in deleting the database")
        else:
            raise web_exception(404, "Company not found")

    def insertField(self, CompanyName, CollectionName, data):
        '''create a collection for a field (dataset for a company)/update a collection\n
                Arguments:
                `CompanyName`: unique name of the company\n
                `CollectionName`: unique name of the collection\n
                `data`: data to be inserted in the collection\n'''
        self.insertDataBase(CompanyName)
        db = self.client[CompanyName]
        collection = db[CollectionName]
        data["_id"] = data.pop("bn")
        collection.insert_one(data)

    def insertDeviceData(self, CompanyName, CollectionName, ID, measure, data):
        '''insert data in a collection\n
                Parameters:
                `CompanyName`-- unique name of the company
                `CollectionName`-- unique name of the collection(a.k.a. field)
                `ID`-- ID of the device
                `measure`-- measure to be inserted in the collection
                `data`-- data to be inserted in the collection'''
        data["_id"] = data.pop("bn")
        counter = 0

        try:
            dict_ = self.client[CompanyName][CollectionName].find_one({
                                                                      "_id": ID})
            if dict_ == None or "e" not in dict_:
                raise KeyError

            found = 0
            for i in dict_["e"]:
                if measure not in dict_["e"][i]["name"]:
                    counter += 1
                else:
                    found = i

            if counter == len(dict_["e"]):
                dict_["e"].append(data["e"][0])
                return
            if isinstance(dict_["e"][found]["value"], list) == False:
                dict_["e"][found]["value"] = [dict_["e"][found]["value"]]
            if isinstance(dict_["e"][found]["value"], list) == False:
                dict_["e"][found]["timestamp"] = [
                    dict_["e"][found]["timestamp"]]
            if isinstance(dict_["e"], list) == False:
                dict_["e"] = [dict_["e"]]
            dict_["e"][found]["value"].extend([data["e"][0]["value"]])
            dict_[ID]["e"][found]["timestamp"].extend(
                [data["e"][0]["timestamp"]])

        except errors.InvalidOperation:
            # means that the device is not in the database, so it is added
            self.client[CompanyName][CollectionName].insert_one(data)
        except KeyError:
            # means that the consumption key of the device was created before the other keys, so it
            # is copied on the data dictionary and the object of the collection is updated
            dict_ = {"consumption": data["consumption"]}
            self.client[CompanyName][CollectionName].update_one(
                {"_id": ID}, {"$set": data})

    def insertTruckData(self, CompanyName, TruckID, data):
        '''insert data in a collection\n
                Parameters:
                `CompanyName`-- unique name of the company
                `CollectionName`-- unique name of the collection(a.k.a. TruckID)
                `data`-- data to be inserted in the collection'''

        db = self.client[CompanyName]
        data["_id"] = data.pop("bn")
        CollectionName = "Trucks"
        dict_ = self.client[CompanyName][CollectionName].find_one({
                                                                  "_id": TruckID})
        if dict_ == None:
            data["e"][0]["v"]["latitude"] = [data["e"][0]["v"]["latitude"]]
            data["e"][0]["v"]["longitude"] = [data["e"][0]["v"]["longitude"]]
            data["e"][0]["v"]["timestamp"] = [data["e"][0]["v"]["timestamp"]]
            self.client[CompanyName][CollectionName].insert_one(data)

        else:
            if (data["e"][0]["v"]["timestamp"] - dict_["e"][0]["v"]["timestamp"][-1]) > 3600:
                # if the truck is not moving for more than an hour, the coordinates database is deleted
                data["e"][0]["v"]["latitude"] = [data["e"][0]["v"]["latitude"]]
                data["e"][0]["v"]["longitude"] = [
                    data["e"][0]["v"]["longitude"]]
                data["e"][0]["v"]["timestamp"] = [
                    data["e"][0]["v"]["timestamp"]]
                self.client[CompanyName][CollectionName].update_one(
                    {"_id": TruckID}, {"$set": data})
            else:

                dict_["e"][0]["v"]["latitude"].append(
                    data["e"][0]["v"]["latitude"])
                dict_["e"][0]["v"]["longitude"].append(
                    data["e"][0]["v"]["longitude"])
                dict_["e"][0]["v"]["timestamp"].append(
                    data["e"][0]["v"]["timestamp"])

                self.client[CompanyName][CollectionName].update_one(
                    {"_id": TruckID}, {"$set": dict_})

    def notify(self, topic, payload):
        '''get data on notification
        Parameters: \n
        `topic` -- string containing the topic of the new message\n
        `payload` -- string containing the payload of the new message\n'''

        listTopic = topic.split("/")
        try:
            if listTopic[2] == "consumption":
                self.insertConsumptionData(listTopic[1], payload)
                # IoTomatoes/CompanyName/consumption
            elif isinstance(int(listTopic[2]), int):
                self.insertDeviceData(
                    listTopic[1], listTopic[2], listTopic[3], listTopic[4], payload)
                # IoTomatoes/CompanyName/Field#/deviceID/measure
            elif listTopic[2] == "truck":
                self.insertTruckData(listTopic[1], listTopic[3], payload)
                # IoTomatoes/CompanyName/truck/truckID
        except IndexError:
            pass

    def checkNewCompany(self):
        '''check if a new company is added by making a GET request to the Resource Catalog'''
        while True:
            try:
                response = requests.get(
                    self.ResourceCatalog_url + "/companies/names")
                response.raise_for_status()
                res_dict = response.json()
            except:
                print("Error in Database")
                return None
            for i in res_dict:
                if i not in list(self.client.list_databases()):
                    self.insertDataBase(i)
            for j in self.client.list_database_names():

                if j not in res_dict and (j != "PlantDatabase" and j != "admin" and j != "local"):
                    print(j)
                    self.deleteDatabase(j)
            time.sleep(20)

    def time_period(self, list, start, end):
        '''get the time period of a list of dates\n
                Parameters:\n
                `list`-- list to be analyzed\n
                `start` -- start date\n
                `end` -- end date \n
                date must be in the format "YYYY-MM-DD '''

        for i in range(len(list)):
            if list[i] <= start:
                start = i
            if list[i] >= end:
                end = i
        if start == (len(list)-1):
            return (start, start)
        elif start == end:
            end += 1
            return (start, end)
        else:
            return (0, 0)

    def GetAvg(self, CompanyName, CollectionName, measure, start, end):
        '''get the average of a measure\n
                Parameters:\n
                `CompanyName` -- unique name of the company\n
           `CollectionName` -- unique name of the collection\n
                `measure` -- measure to be calculated\n
                `start` -- start date of the period\n
                `end` -- end date of the period\n
                date must be in the format "YYYY-MM-DD 
                if the last value of the timestamp is put as start, the result will be empty'''

        if CompanyName in self.client.list_database_names():
            if CollectionName in self.client[CompanyName].list_collection_names():
                db = self.client[CompanyName]
                collection = db[CollectionName]
                dict = list(collection.find())
                lst = []
                avg = 0
                flag = 0
                indexes_to_get_unit = []
                for i in range(len(dict)):

                    for j in range(len(dict[i]["e"])):
                        if dict[i]["e"][j]["name"] == measure:
                            indexes = self.time_period(
                                dict[i]["e"][j]["timestamp"], start, end)
                            avg = sum(dict[i]["e"][j]["value"][indexes[0]:indexes[1]]) / \
                                len(dict[i]["e"][j]["value"]
                                    [indexes[0]:indexes[1]])
                            lst.append(avg)
                            indexes_to_get_unit = [i, j]
                            flag = 1

                if len(lst) == 0 or flag == 0:
                    return False
                else:
                    result = {
                        "Company": CompanyName,
                        "Field": CollectionName,
                        "Measure": measure,
                        "Average": sum(lst)/len(lst),
                        "Unit": dict[indexes_to_get_unit[0]]["e"][indexes_to_get_unit[1]]["unit"],
                        "Time Period": [start, end]
                    }
                return json.dumps(result)
            else:
                raise web_exception(404, "Field not found")
        else:
            raise web_exception(404, "Company not found")

    def getAvgAll(self, CompanyName, measure, start, end):
        '''get the average of a measure for all the fields of a company\n
                Parameters:\n
                `CompanyName` -- unique name of the company\n
                `measure` -- measure to be calculated\n
                `start` -- start date of the period\n
                `end` -- end date of the period\n'''
        if CompanyName in self.client.list_database_names():
            db = self.client[CompanyName]
            lst = []
            unit = "No unit"
            for i in db.list_collection_names():
                if "Field" in i:
                    result = self.GetAvg(CompanyName, i, measure, start, end)
                    if result is not False and result is not None:
                        result = json.loads(result)
                        lst.append(result["Average"])
                        unit = result["Unit"]
            if len == [] or unit == "No unit":
                raise web_exception(404, "No data found")

            resultDict = {"Company": CompanyName, "Measure": measure, "Average": sum(
                lst)/len(lst), "Unit": unit, "Timeperiod": [start, end]}
            return json.dumps(resultDict)
        else:
            raise web_exception(404, "No company found")

    def getMeasureGraphData(self, CompanyName, CollectionName, measure, start, end):
        '''get the data needed for a graph a field of a company\n
        Parameters:\n
        `CompanyName` -- unique name of the company\n
        `collectionName` -- field of the company\n
        `measure` -- measure /actuator to plot\n
        `start` -- start date of the period\n
        `end` -- end date of the period\n
        '''

        if CompanyName in self.client.list_database_names():
            if CollectionName in self.client[CompanyName].list_collection_names():
                db = self.client[CompanyName]
                collection = db[CollectionName]
                dict_ = list(collection.find())
                lst = []
                timestamps = []
                resultDict = {}
                unit = "No unit"
                for i in range(len(dict_)):
                    lst = []
                    timestamps = []
                    for j in range(len(dict_[i]["e"])):
                        if dict_[i]["e"][j]["name"] == measure:
                            indexes = self.time_period(
                                dict_[i]["e"][j]["timestamp"], start, end)
                            lst.extend(dict_[i]["e"][j]["value"]
                                       [indexes[0]:indexes[1]])
                            timestamps.extend(
                                dict_[i]["e"][j]["timestamp"][indexes[0]:indexes[1]])
                            unit = dict_[i]["e"][j]["unit"]
                    resultDict[dict_[i]["_id"]] = {
                        "values": lst, "timestamps": timestamps, "unit": unit}
                return json.dumps(resultDict)
            else:
                raise web_exception(404, "Field not found")
        else:
            raise web_exception(404, "Company not found")

    def insertConsumptionData(self, CompanyName, data):
        '''insert data coming from the consumption service\n
        Parameters:\n
        `companyName`-- unique name of the company\n
        `data`-- JSON coming from the consumption service\n'''
        db = self.client[CompanyName]
        data["_id"] = data.pop("bn")
        ID = data["_id"]
        consumptionData = data["consumption"]
        consumptionValue = consumptionData["consumption_value"]
        timestamp = consumptionData["timestamp"]
        power = consumptionData["power"]
        CollectionName = data["field"]
        collection = db[CollectionName]
        dict = list(collection.find())
        self.insertDataBase(CompanyName)

        try:
            # update consumption_value,power and timestamp list
            dict[ID]["consumption"]["consumption_value"].append(
                consumptionValue)
            dict[ID]["consumption"]["power"].append(power)
            dict[ID]["consumption"]["timestamp"].append(timestamp)
            collection.update_one({"_id": ID}, {"$set": dict[ID]})
        except KeyError:
            # if KeyError raise, it means that the consumption dictionary is not present in the field colleciton
            # yet, so it is created
            dict[ID]["consumption"] = data["consumption"]
            dict[ID]["consumption"]["consumption_value"] = [
                dict[ID]["consumption"]["consumption_value"]]
            dict[ID]["consumption"]["power"] = [
                dict[ID]["consumption"]["power"]]
            dict[ID]["consumption"]["timestamp"] = [
                dict[ID]["consumption"]["timestamp"]]
            collection.update_one({"_id": ID}, {"$set": dict[ID]})
        except AttributeError:
            # if AttributeError raise, it means that the values of the dictionary are not lists, so they are converted
            dict[ID]["consumption"]["consumption_value"] = [
                dict[ID]["consumption"]["consumption_value"]]
            dict[ID]["consumption"]["power"] = [
                dict[ID]["consumption"]["power"]]
            dict[ID]["consumption"]["timestamp"] = [
                dict[ID]["consumption"]["timestamp"]]
            dict[ID]["consumption"]["consumption_value"].append(
                consumptionValue)
            dict[ID]["consumption"]["power"].append(power)
            dict[ID]["consumption"]["timestamp"].append(timestamp)
            collection.update_one({"_id": ID}, {"$set": dict[ID]})

    def getConsumptionData(self, CompanyName, start, end):
        '''get the consumption data of a field of a company\n
        Parameters:\n
        `CompanyName`-- unique name of the company\n
        `CollectionName`-- field of the company\n
        `start`-- start date of the period\n
        `end`-- end date of the period\n'''
        if CompanyName in self.client.list_database_names():
            for CollectionName in self.client[CompanyName].list_collection_names():
                if "Field" in CollectionName:
                    db = self.client[CompanyName]
                    collection = db[CollectionName]
                    dict_ = list(collection.find())
                    lst = []
                    timestamps = []
                    resultDict = {}
                    unit = "No unit"
                    try:
                        for i in range(len(dict_)):
                            lst = []
                            timestamps = []
                            if "consumption" in dict_[i].keys():
                                indexes = self.time_period(
                                    dict_[i]["consumption"]["timestamp"], start, end)
                                lst.extend(
                                    dict_[i]["consumption"]["consumption_value"][indexes[0]:indexes[1]])
                                timestamps.extend(
                                    dict_[i]["consumption"]["timestamp"][indexes[0]:indexes[1]])
                                unit = dict_[i]["consumption"]["unit"]
                            resultDict[CollectionName] = {"values": sum(
                                lst), "timestamps": timestamps, "unit": unit}
                    except KeyError:
                        pass
                    if resultDict == {}:
                        raise web_exception(404, "No consumption data found")
                    return json.dumps(resultDict)
        else:
            raise web_exception(404, "No company found")

    def getPlant(self, PlantName):
        '''get the plant informations\n
        Parameters:\n
        `PlantName`-- unique name of the plant\n'''
        db = self.client["PlantDatabase"]
        collection = db["PlantData"]
        dict = list(collection.find())
        for i in dict:
            if i["PlantName"] == PlantName:
                return json.dumps(i)
        raise web_exception(404, "Plant not found")

    def getTruckTrace(self, CompanyName, TruckID):
        '''get the truck trace informations\n
        Parameters:\n
        `TruckID`-- unique ID of the truck\n'''

        dict_ = self.client[CompanyName]["TruckData"].find_one(
            {"TruckID": TruckID})
        if dict_ != None:
            lat = dict_["e"][0]["v"]["latitude"]
            lon = dict_["e"][0]["v"]["longitude"]
            return json.dumps({"latitude": lat, "longitude": lon})
        else:
            raise web_exception(404, "Truck not found")

    def getTruckPosition(self, CompanyName):
        '''get the truck trace informations\n'''
        dict_ = self.client[CompanyName]["Trucks"].find()
        returnDict = {}
        for i in dict_:
            returnDict[dict_[i]["_id"]] = {"latitude": dict_[
                i]["e"][0]["v"]["latitude"], "longitude": dict_[i]["e"][0]["v"]["longitude"]}
        return json.dumps(returnDict)


class RESTConnector(BaseService):
    exposed = True

    def __init__(self, settings: dict):

        super().__init__(settings)
        self.mongo = MongoConnection(
            self.ResourceCatalog_url, settings["MongoDB_Url"], settings["PlantDatabaseName"])

    def GET(self, *uri, **params):
        """GET method for the REST API\n
        Returns a JSON with the requested information\n
        Allowed URI:\n
        `/Avg`: returns the average of the measures requested.\n 
        The parameters are "CompanyName", "Field" and "measure", "starting date", "end date"\n
        if `params["Field"]` == "all" returns the average of all field of corresponding company\n
        `/plant`: returns the plant informations\n
        The parameter is "PlantName"\n"""

        try:
            if len(uri) > 0:
                if len(uri) == 1 and uri[0] == "avg" and params["Field"] != "all":
                    return self.mongo.GetAvg(params["CompanyName"], params["Field"], params["measure"], params["start_date"], params["end_date"])
                elif len(uri) == 1 and uri[0] == "avg" and params["Field"] == "all":
                    return self.mongo.getAvgAll(params["CompanyName"], params["measure"], params["start_date"], params["end_date"])
                elif len(uri) == 1 and uri[0] == "plant":
                    return self.mongo.getPlant(params["PlantName"])
                elif len(uri) == 1 and uri[0] == "truckTrace":
                    return self.mongo.getTruckTrace(params["CompanyName"], params["TruckID"])
                elif len(uri) == 1 and uri[0] == "truckPosition":
                    return self.mongo.getTruckPosition(params["CompanyName"])
                elif len(uri) == 1 and uri[0] == "graph":
                    return self.mongo.getMeasureGraphData(params["CompanyName"], params["Field"], params["measure"], params["start_date"], params["end_date"])
                elif len(uri) == 1 and uri[0] == "consumption":
                    return self.mongo.getConsumptionData(params["CompanyName"], params["start_date"], params["end_date"])

                else:
                    raise web_exception(404, "Resource not found.")
        except web_exception as e:
            raise cherrypy.HTTPError(e.code, e.message)
        except:
            raise cherrypy.HTTPError(500, "Internal Server Error")


def sigterm_handler(signal, frame):
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
