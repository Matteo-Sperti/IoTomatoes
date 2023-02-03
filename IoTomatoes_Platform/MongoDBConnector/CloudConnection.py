from pymongo import MongoClient
from pymongo import errors
import json
import time
import cherrypy
import requests
from matplotlib import pyplot as plt
import datetime
from socket import gethostname, gethostbyname

from iotomatoes_supportpackage.BaseService import BaseService
from iotomatoes_supportpackage.MyExceptions import web_exception

class MongoConnection():
	def __init__(self, ResourceCatalog_url : str, MongoDB_url : str, PointsPerGraph : int):
		self.ResourceCatalog_url = ResourceCatalog_url
		self.MongoDB_url = MongoDB_url
		self.PointsPerGraph = PointsPerGraph
		try:
			self.client = MongoClient(self.MongoDB_url)
		except errors.AutoReconnect:
			print("Error connecting to the database")
		else:
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
		self.insertDataBase(CompanyName)
		db = self.client[CompanyName]
		collection = db[CollectionName]
		data["_id"]=data.pop("bn")
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
		counter=0
	
		try:
			dict_ = self.client[CompanyName][CollectionName].find_one({"_id":ID})
			if dict_ == None or "e" not in dict_:
				raise KeyError
			
			found = 0
			for i in dict_["e"]:
				if measure not in dict_["e"][i]["name"]:
					counter+=1
				else :
					found = i
			
			if counter == len(dict_["e"]):
				raise Exception("measure not found")    
			if isinstance(dict_["e"][found]["value"],list) == False:
				dict_["e"][found]["value"]=[dict_["e"][found]["value"]]
			if isinstance(dict_["e"][found]["value"],list) == False:
				dict_["e"][found]["timestamp"]=[dict_["e"][found]["timestamp"]]
			if isinstance(dict_["e"],list) == False:
				dict_["e"]=[dict_["e"]]
			dict_["e"][found]["value"].extend([data["e"][0]["value"]])
			dict_[ID]["e"][found]["timestamp"].extend([data["e"][0]["timestamp"]])

		except errors.InvalidOperation:
			#means that the device is not in the database, so it is added
			self.client[CompanyName][CollectionName].insert_one(data)
		except KeyError:
			#means that the consumption key of the device was created before the other keys, so it
			#is copied on the data dictionary and the object of the collection is updated
			data["consumption"]=dict_["consumption"]
			self.client[CompanyName][CollectionName].update_one({"_id":ID}, {"$set": data})
		except Exception as e:
			#the device is in the database but the measure is not,so it is added
			if str(e) == "measure not found":
				dict_["e"].append(data["e"][0])
				
	def notify(self,topic, payload):
			'''get data on notification
			Parameters: \n
			`topic` -- string containing the topic of the new message\n
			`payload` -- string containing the payload of the new message\n'''
			
			listTopic=topic.split("/")
			try:
				if listTopic[2] == "consumption":
					self.insertConsumptionData(listTopic[1],payload)
					#IoTomatoes/CompanyName/consumption    
				elif isinstance(int(listTopic[2]),int):
					self.insertDataSensors(listTopic[1],listTopic[2],listTopic[3],listTopic[4],payload)
					#IoTomatoes/CompanyName/Field#/deviceID/measure
			except IndexError:
					pass
			
			
		
	def checkNewCompany(self):
			'''check if a new company is added by making a GET request to the Resource Catalog'''
			while True:
				response = requests.get(self._() + "/CompaniesName")
				list = json.loads(response)
				for i in list:
					if i not in self.client.list_database_names():
						self.insertDataBase(i)
				time.sleep(300)
				
	def time_period(self,list,start,end):
		'''get the time period of a list of dates\n
			Parameters:\n
			`list`-- list to be analyzed\n
			`start` -- start date\n
			`end` -- end date \n
			date must be in the format "YYYY-MM-DD '''

		for i in range(len(list)):
			if list[i]<=start:
				start=i
			if list[i]>=end:
				end=i
		if start== (len(list)-1):
			return(start,start)
		elif start == end:
			end+=1
			return (start,end)       
				
	def GetAvg(self,CompanyName,CollectionName,measure,start,end):
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
				dict =list(collection.find())
				lst=[]
				
				for i in range(len(dict)):
					
					for j in range(len(dict[i]["e"])):
						if dict[i]["e"][j]["name"] == measure:
							indexes=self.time_period(dict[i]["e"][j]["timestamp"],start,end)
							lst.extend(dict[i]["e"][j]["value"][indexes[0]:indexes[1]])
							indexes_to_get_unit=[i,j]
				if len(lst)==0:
					return False
				else:
					result={
							"Company": CompanyName,
	     					"Field": CollectionName,
							"Measure": measure,
							"Average": sum(lst)/len(lst),
							"Unit": dict[indexes_to_get_unit[0]]["e"][indexes_to_get_unit[1]]["unit"],
							"Time Period" : [start,end]
						}
				return json.dumps(result)
			else:
				return False
		else:
			print("Database does not exist")

	def getAvgAll(self,CompanyName,measure,start,end):
		'''get the average of a measure for all the fields of a company\n
			Parameters:\n
			`CompanyName` -- unique name of the company\n
			`measure` -- measure to be calculated\n
			`start` -- start date of the period\n
			`end` -- end date of the period\n'''
		if CompanyName in self.client.list_database_names():
			db = self.client[CompanyName]
			lst=[]
			for i in db.list_collection_names():
				if i != "CompanyData":
					result = self.GetAvg(CompanyName,i,measure,start,end)
					if len("result" not in result):
						result=json.loads(result)
						list.append(result["Average"])
						unit = result["Unit"]
			
			resultDict = {"Company":CompanyName,"Measure":measure,"Average":sum(lst)/len(lst),"Unit":unit,"Timeperiod":[start,end]}                       
			return json.dumps(resultDict)
		else:
			return False
		
	def insertConsumptionData(self,CompanyName,data):
		'''insert data coming from the consumption service\n
		Parameters:\n
		`companyName`-- unique name of the company\n
		`data`-- JSON coming from the consumption service\n'''
		db = self.client[CompanyName]
		data["_id"]=data.pop("bn")
		ID = data["_id"]
		consumptionData=data["consumption"]
		consumptionValue=consumptionData["consumption_value"]
		timestamp=consumptionData["timestamp"]
		power=consumptionData["power"]
		CollectionName = data["field"]
		collection = db[CollectionName]
		dict = list(collection.find()) 
		self.insertDataBase(CompanyName)
		
		try:
			#update consumption_value,power and timestamp list
			dict[ID]["consumption"]["consumption_value"].append(consumptionValue)
			dict[ID]["consumption"]["power"].append(power)
			dict[ID]["consumption"]["timestamp"].append(timestamp)
			collection.update_one({"_id":ID}, {"$set": dict[ID]})
		except KeyError:
			#if KeyError raise, it means that the consumption dictionary is not present in the field colleciton
			#yet, so it is created
			dict[ID]["consumption"]=data["consumption"]
			dict[ID]["consumption"]["consumption_value"]=[dict[ID]["consumption"]["consumption_value"]]
			dict[ID]["consumption"]["power"]=[dict[ID]["consumption"]["power"]]
			dict[ID]["consumption"]["timestamp"]=[dict[ID]["consumption"]["timestamp"]]
			collection.update_one({"_id":ID}, {"$set": dict[ID]})
		except AttributeError:
			#if AttributeError raise, it means that the values of the dictionary are not lists, so they are converted
			dict[ID]["consumption"]["consumption_value"]=[dict[ID]["consumption"]["consumption_value"]]
			dict[ID]["consumption"]["power"]=[dict[ID]["consumption"]["power"]]
			dict[ID]["consumption"]["timestamp"]=[dict[ID]["consumption"]["timestamp"]]
			dict[ID]["consumption"]["consumption_value"].append(consumptionValue)
			dict[ID]["consumption"]["power"].append(power)
			dict[ID]["consumption"]["timestamp"].append(timestamp)
			collection.update_one({"_id":ID}, {"$set": dict[ID]})

	def getGraphMeasure(self,CompanyName,CollectionName,measure,start,end):
		'''get the graph of a measure for a field of a company\n
		Parameters:\n
		`CompanyName` -- unique name of the company\n
		`collectionName` -- field of the company\n
		`Measure` -- measure to be calculated\n
		`Start` -- start date of the period\n
		`end` -- end date of the period\n'''

		if CompanyName in self.client.list_database_names():
			if CollectionName in self.client[CompanyName].list_collection_names():
				db = self.client[CompanyName]
				collection = db[CollectionName]
				dict =list(collection.find())
				lst=[]
				timestamps=[]
								
				for i in range(len(dict)):
					
					for j in range(len(dict[i]["e"])):
						if dict[i]["e"][j]["name"] == measure:
							indexes=self.time_period(dict[i]["e"][j]["timestamp"],start,end)
							lst.extend(dict[i]["e"][j]["value"][indexes[0]:indexes[1]])
							timestamps.extend(dict[i]["e"][j]["timestamp"][indexes[0]:indexes[1]])
							indexes_to_get_unit=[i,j]
				unit = dict[indexes_to_get_unit[0]]["e"][indexes_to_get_unit[1]]["unit"]
				#get 7 timestamps points
				if len(timestamps)/self.PointsPerGraph > 1:
					step = int(len(timestamps)/self.PointsPerGraph)
					timestamps = timestamps[::step]
				for i in range(len(timestamps)):
					lst.append(json.loads(self.GetAvg(CompanyName,CollectionName,measure,0,timestamps[i]))["Average"])
				#convert timestamps to normal time
				for i in range(len(timestamps)):
					timestamps[i]=datetime.fromtimestamp(timestamps[i])
				#plot graph
				plt.plot(timestamps,lst)
				plt.xlabel("Time")
				plt.ylabel(measure+" ("+unit+")")
				plt.title("Graph of "+measure+" for "+CollectionName+" of "+CompanyName)
				plt.savefig("graph.png")
				#capire con fede come passare l'immagine
			
def getGraphActuator(self,CompanyName,CollectionName,Actuator,start,end):
		'''get pie chart of actuators's status of a field of a company\n
		Multiple actuator can be monitored at the same time\n
		Parameters:\n
		`CompanyName` -- unique name of the company\n
		`collectionName` -- field of the company\n
		`Actuator` -- actuator to be monitor (either pump or led)\n
		`Start` -- start date of the period\n
		`end` -- end date of the period\n'''
		#da finire
		if CompanyName in self.client.list_database_names():
			if CollectionName in self.client[CompanyName].list_collection_names():
				db = self.client[CompanyName]
				collection = db[CollectionName]
				dict =list(collection.find())
				dict_values={}
				timestamps=[]
				counter1=0
				counter0=0
				for i in range(len(dict)):
					
					for j in range(len(dict[i]["e"])):
						if dict[i]["e"][j]["name"] == Actuator:
							indexes=self.time_period(dict[i]["e"][j]["timestamp"],start,end)
							dict_values[dict[i]["_id"]]=dict[i]["e"][j]["value"][indexes[0]:indexes[1]]
							for i in range(len(dict_values[dict[i]["_id"]])):
								if dict_values[dict[i]["_id"]][i] == 1:
									counter1+=1
								else:
									counter0+=1
							plt.pie([counter1,counter0],labels=["ON","OFF"])
							plt.title("Graph of "+Actuator+" for "+CollectionName+" of "+CompanyName)
							plt.savefig("graph"+dict[i]["_id"]+".png")

class RESTConnector(BaseService):
	exposed = True
	def __init__(self,settings:dict):
		
		super().__init__(settings)
		self.mongo = MongoConnection(self.ResourceCatalog_url, settings["MongoDB_Url"], settings["PointsPerGraph"])
		
	def GET(self, *uri, **params):
		"""GET method for the REST API\n
		Returns a JSON with the requested information\n
		Allowed URI:\n
		`/Avg`: returns the average of the measures requested.\n 
		The parameters are "CompanyName", "Field" and "measure", "starting date", "end date"\n
		if `params["Field"]` == "all" returns the average of all field of corresponding company\n"""
		try:
			if len(uri) > 0:
				if len(uri) == 1 and uri[0] == "avg" and params["Field"] != "all":
					return self.mongo.GetAvg(params["CompanyName"],params["Field"],params["measure"],params["start_date"],params["end_date"])
				elif len(uri) == 1 and uri[0] == "avg" and params["Field"] == "all":                    
					return self.mongo.getAvgAll(params["CompanyName"],params["measure"],params["start_date"],params["end_date"])
				else:
					raise web_exception(404, "Resource not found.")
		except web_exception as e:
			raise cherrypy.HTTPError(e.code, e.message)
		except:
			raise cherrypy.HTTPError(500, "Internal Server Error")

		
if __name__ == "__main__":
	settings = json.load(open("ConnectorSettings.json"))

	ip_address = gethostbyname(gethostname())
	port = settings["IPport"]
	settings["IPaddress"] = ip_address

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

	try:
		while True:
			time.sleep(3)
	except KeyboardInterrupt or SystemExit:
		WebService.stop()
		cherrypy.engine.exit()
		print("Server stopped")
