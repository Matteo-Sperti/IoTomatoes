import json
import requests
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import sys

sys.path.append("../SupportClasses/")
from MyExceptions import *


keyboardYESNO = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='YES ✅', callback_data='yes'),
                InlineKeyboardButton(text='NO ❌', callback_data='no'),
            ]])

class InsertNewCompany():
    def __init__(self, chatID, sender, connector):
        self.chatID = chatID
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.response = {}

    @property
    def adminInfo(self):
        return {"Name" : self.response["Name"], 
                "Surname" : self.response["Surname"], 
                "telegramID" : self.chatID}

    @property
    def company(self):
        return {"CompanyName": self.response["CompanyName"], 
                "CompanyToken": self.response["CompanyToken"],
                "Location" : self.location,
                "NumberOfFields" : self.response["NumberOfFields"]}

    @property
    def location(self):
        return self.response["Location"]

    def update(self, message): 
        if self._status == 0:
            self._bot.sendMessage("Insert your Company Name")
            self._status += 1
        
        elif self._status == 1:
            self.response["CompanyName"] = message
            self._bot.sendMessage("Insert your Name")
            self._status += 1

        elif self._status == 2:
            self.response["Name"] = message
            self._bot.sendMessage("Insert your Surname")
            self._status += 1
        
        elif self._status == 3:
            self.response["Surname"] = message
            self._bot.sendMessage("Insert your Company Token")
            self._status += 1

        elif self._status == 4:
            self.response["CompanyToken"] = message
            self._bot.sendMessage(f"Your Company Token is: {message}\nProceed with the registration?",
                                    reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 5:
            if message == "yes":
                self._bot.sendMessage("Insert your location as couple of coordinates:")
                self._status += 1
            else:
                self._bot.sendMessage("Insert your Company Token")
                self._status = 4

        elif self._status == 6:
            try:
                message.replace(" ", "")
                latitude, longitude = message.split(",")
                self.response["Location"] = {
                    "longitude" : float(longitude),
                    "latitude" : float(latitude)
                }           
                self._bot.sendLocation(self.location["latitude"], self.location["longitude"])
            except:
                self._bot.sendMessage("Invalid location")
                self._bot.sendMessage("Insert your location as couple of coordinates:")
                self._status = 6
            else:
                self._bot.sendMessage(f"Is this your location?", reply_markup=keyboardYESNO)
                self._status += 1

        elif self._status == 7:
            if message == "yes":
                self._bot.sendMessage("How many indipendent fields do you have in your company?")
                self._status += 1
            else:
                self._bot.sendMessage("Insert your location as couple coordinates:")
                self._status = 6

        elif self._status == 8:
            try:
                self.response["NumberOfFields"] = int(message)
            except:
                self._bot.sendMessage("Invalid number, please insert a positive integer number")
                self._bot.sendMessage("How many indipendent fields do you have in your company?")
                self._status = 8
            else:
                self._bot.sendMessage("Insert the colture of your fields, separated by a comma")
                self._status += 1

        elif self._status == 9:
            try:
                fields = message.split(",")
                if len(fields) != self.response["NumberOfFields"]:
                    raise ValueError

                self.response["fieldsList"] = []
                for i, field in enumerate(fields):
                    self.response["fieldsList"].append({
                        "fieldNumber" : i+1,
                        "plant" : field.lower().strip()
                    })
            except:
                self._bot.sendMessage("Invalid input")
                self._bot.sendMessage("Insert the colture of your fields, separated by a comma")
                self._status = 9
            else:
                summary = (f"You are going to register the following company:\n"
                            f"Company Name: {self.response['CompanyName']}\n"
                            f"Company Token: {self.response['CompanyToken']}\n"
                            f"Location: {self.location['latitude']}, {self.location['longitude']}\n\n"
                            f"{self.response['Name']} {self.response['Surname']} will be the admin of this company\n")
                self._bot.sendMessage(summary)
                self._bot.sendMessage("Confirm your registration?", reply_markup=keyboardYESNO)
                self._status += 1

        elif self._status == 10:
            if message == "yes":
                if self.insert_company():
                    self._bot.sendMessage("Registration completed")
                else:
                    self._bot.sendMessage("Registration failed")
            else:
                self._bot.sendMessage("Registration canceled")
            return True
            
    def insert_company(self):   
        try:
            params = self.company
            params.update({"SystemToken" : self._connector._SystemToken})
            body = {"AdminInfo" : self.adminInfo, "fieldsList" : self.response["fieldsList"]}
            res = requests.post(self._connector.ResourceCatalog_url + "/insertCompany", params=params, 
                                    data= json.dumps(body))
            res.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            print(f"Error in the connection with the Resource Catalog\n")
            return False
        else:
            try:
                res_dict = res.json()
                if res_dict["Status"]:
                    CompanyID = res_dict["CompanyID"]
                    CompanyToken = res_dict["CompanyToken"]
                    message = (f"""Company {self.company["CompanyName"]} registered\n"""
                            "Welcome to IoTomatoes Platform\n\n"
                            f"CompanyID: {CompanyID}\n"
                            f"CompanyToken: {CompanyToken}")
                    self._bot.sendMessage(message)
                    return True
                else:
                    if "Error" in res_dict:
                        if res_dict["Error"] == "Company already registered":
                            self._bot.sendMessage("Company already registered")
                    print(f"Denied by the Resource Catalog\n")
                    return False
            except:
                print(f"Error in the information\n")
                return False

class RegisterNewUser():
    def __init__(self, chatID, sender, connector):
        self.chatID = chatID
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.response = {}

    @property
    def UserInfo(self):
        return {"Name" : self.response["Name"], "Surname" : self.response["Surname"], "telegramID" : self.chatID}

    @property
    def completeName(self):
        return f"{self.UserInfo['Name']} {self.UserInfo['Surname']}"

    @property
    def company(self):
        return {"CompanyName": self.response["CompanyName"], "CompanyToken" : self.response["CompanyToken"]}

    def update(self, message):            
        if self._status == 0:
            self._bot.sendMessage("Insert your Company Name")
            self._status += 1

        elif self._status == 1:
            self.response["CompanyName"] = message
            self._bot.sendMessage("Insert your Name")
            self._status += 1

        elif self._status == 2:
            self.response["Name"] = message
            self._bot.sendMessage("Insert your Surname")
            self._status += 1
        
        elif self._status == 3:
            self.response["Surname"] = message
            self._bot.sendMessage("Insert your Company Token")
            self._status += 1

        elif self._status == 4:
            self.response["CompanyToken"] = message
            summary = (f"You are going to register {self.completeName} as a new user of {self.response['CompanyName']}\n"
                        f"Company Token: {self.response['CompanyToken']}\n")
            self._bot.sendMessage("Confirm your registration?", reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 5:
            if message == "yes":
                if self.insert_user():
                    self._bot.sendMessage("Registration completed")
                else:
                    self._bot.sendMessage("Registration failed")
            else:
                self._bot.sendMessage("Registration canceled")
            return True

    def insert_user(self):
        try:
            res = requests.post(self._connector.ResourceCatalog_url + f"/insert/user", 
                                    params=self.company, json=self.UserInfo)
            res.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            elif err.response.status_code == 401:
                self._bot.sendMessage("CompanyToken not valid")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            print(f"Error in the connection with the Resource Catalog\n")
            return False
        else:
            try:
                res_dict = res.json()
                UserID = res_dict["ID"]
                message = (f"""User {self.completeName} registered in company {self.company["CompanyName"]}\n"""
                        "Welcome to IoTomatoes Platform\n\n"
                        f"UserID: {UserID}\n")
                self._bot.sendMessage(message)
                return True
            except:
                print(f"Error in the information\n")
                return False

def getUsers(CompanyName : str, bot, connector) -> None:
    users = connector.getList(CompanyName, "users")
    if users is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(users) == 0:
        bot.sendMessage(f"No users registered in {CompanyName}")
    else:
        message = (f"Users in {CompanyName}:\n\n")
        bot.sendMessage(message)
        for user in users:
            message = (f"Name: {user['Name']}\n"
                                f"Surname: {user['Surname']}\n"
                                f"UserID: {user['ID']}\n\n")
            bot.sendMessage(message)
        

def getDevices(CompanyName : str, bot, connector) -> None:
    devices = connector.getList(CompanyName, "devices")
    if devices is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(devices) == 0:
        bot.sendMessage(f"No devices registered in {CompanyName}")
    else:
        if devices != None:
            message = (f"Devices in {CompanyName}:\n\n")
            bot.sendMessage(message)
            for device in devices:
                message = (f"Device Name: {device['deviceName']}\n"
                            f"DeviceID: {device['ID']}\n"
                            f"Location: {device['Location']['Latitude']}, {device['Location']['Longitude']}\n")
                if device["isActuator"]:
                    act_msg = f"Actuators: " + ", ".join(device["actuatorType"])
                    message = message + act_msg +"\n"
                if device["isSensor"]:
                    sens_msg = f"Sensors: " + ", ".join(device["measureType"])
                    message = message + sens_msg +"\n"
                bot.sendMessage(message)

def getFields(CompanyName : str, bot, connector) -> None:
    fields = connector.getList(CompanyName, "fields")
    if fields is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(fields) == 0:
        bot.sendMessage(f"No fields registered in {CompanyName}")
    else:
        if fields != None:
            message = (f"Fields in {CompanyName}:\n\n")
            bot.sendMessage(message)
            for field in fields:
                message = (f"Field number: {field['fieldNumber']}\n"
                            f"plant: {field['plant']}\n")
                bot.sendMessage(message)

class DeleteCompany():
    def __init__(self, CompanyName : str, chatID, sender, connector):
        self.chatID = chatID
        self.CompanyName = CompanyName
        self.CompanyToken = ""
        self._connector = connector
        self._bot = sender
        self._status = 0

    def update(self, message):
        if self._status == 0:
            self._bot.sendMessage("You are going to delete company " + self.CompanyName)
            self._bot.sendMessage("Insert your Company Token")
            self._status += 1
        
        elif self._status == 1:
            self.CompanyToken = message
            self._bot.sendMessage("Confirm your deletion?", reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 2:
            if message == "yes":
                if self.delete_company():
                    self._bot.sendMessage("Deletion completed")
                else:
                    self._bot.sendMessage("Deletion failed")
            else:
                self._bot.sendMessage("Deletion canceled")
            return True

    def delete_company(self):
        try:
            params = {"CompanyName" : self.CompanyName, "CompanyToken" : self.CompanyToken, "telegramID" : self.chatID}
            res = requests.delete(self._connector.ResourceCatalog_url + "/company", 
                                    params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            elif err.response.status_code == 401:
                self._bot.sendMessage("CompanyToken not valid")
            elif err.response.status_code == 403:
                self._bot.sendMessage("You are not authorized to delete this company.\nContact your administrator.")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            self._bot.sendMessage("Error in the connection with the Resource Catalog")
            return False
        else:
            if "Status" in dict_ and dict_["Status"]:
                return True
            else:
                return False

class ChangePlant():
    def __init__(self, CompanyName : str, sender, connector):
        self.CompanyName = CompanyName
        self.CompanyToken = ""
        self.FieldNumber = ""
        self.newplant = ""
        self._connector = connector
        self._bot = sender
        self._status = 0

    def update(self, message):
        if self._status == 0:
            fields = self._connector.getList(self.CompanyName, "fields")
            if fields == None:
                self._bot.sendMessage("Error in the connection with the Resource Catalog")
                return True
            elif len(fields) == 0:
                self._bot.sendMessage("No fields registered")
                return True
            else:
                inline_keyboard_ = []
                for field in fields:
                    number = field['fieldNumber']
                    plant = field['plant']
                    button = InlineKeyboardButton(text=f"F{number} : {plant}", callback_data=f"{number}")
                    inline_keyboard_.append([button])
                keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard_)
                self._bot.sendMessage(f"Which field of company {self.CompanyName} do you want to change?",
                                        reply_markup=keyboard)
                self._status += 1
        
        elif self._status == 1:
            try: 
                self.FieldNumber = int(message)
            except:
                self._bot.sendMessage("Field number must be an integer")
                self._status += 0
            else:
                self._bot.sendMessage("Insert the new plant")
                self._status += 1

        elif self._status == 2:
            self.newplant = message
            self._bot.sendMessage("Insert your Company Token")
            self._status += 1

        elif self._status == 3:
            self.CompanyToken = message
            change = f"You are changing the plant of field {self.FieldNumber} of company {self.CompanyName} to {self.newplant}"
            self._bot.sendMessage(f"{change}\nConfirm your change?", reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 4:
            if message == "yes":
                if self.change_plant():
                    self._bot.sendMessage("Update of field completed")
                else:
                    self._bot.sendMessage("Update of field failed")
            else:
                self._bot.sendMessage("Update of field canceled")
            return True

    def change_plant(self):
        try:
            params = {"CompanyName" : self.CompanyName, 
                    "CompanyToken" : self.CompanyToken,
                    "fieldNumber" : self.FieldNumber,
                    "plant" : self.newplant}
            res = requests.put(self._connector.ResourceCatalog_url + "/field", 
                                    params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            elif err.response.status_code == 401:
                self._bot.sendMessage("CompanyToken not valid")
            elif err.response.status_code == 403:
                self._bot.sendMessage("You are not authorized to delete this company.\nContact your administrator.")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            self._bot.sendMessage("Error in the connection with the Resource Catalog")
            return False
        else:
            if "Status" in dict_ and dict_["Status"]:
                return True
            else:
                return False

class CustomPlot():
    def __init__(self, CompanyName : str, sender, connector):
        self.CompanyName = CompanyName
        self.CompanyToken = ""
        self._connector = connector
        self._bot = sender
        self._status = 0

        self._bot.sendMessage("not implemented yet")

    def update(self, message):
        return True