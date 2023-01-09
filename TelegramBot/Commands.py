import json
import requests
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

keyboardYESNO = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='YES ✅', callback_data='yes'),
                InlineKeyboardButton(text='NO ❌', callback_data='no'),
            ]])

class InsertNewCompany():
    def __init__(self, chatID, sender, connector):
        self.chatID = chatID
        self.completed = False
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.response = {}
        self.update("")

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
                summary = (f"You are going to register the following company:\n"
                            f"Company Name: {self.response['CompanyName']}\n"
                            f"Company Token: {self.response['CompanyToken']}\n"
                            f"Location: {self.location['latitude']}, {self.location['longitude']}\n\n"
                            f"{self.response['Name']} {self.response['Surname']} will be the admin of this company\n")
                self._bot.sendMessage(summary)
                self._bot.sendMessage("Confirm your registration?", reply_markup=keyboardYESNO)
                self._status += 1

        elif self._status == 9:
            if message == "yes":
                if not self.insert_company():
                    self._bot.sendMessage("Registration failed")
                else:
                    self._bot.sendMessage("Registration completed")
            else:
                self._bot.sendMessage("Registration canceled")
            self.completed = True
            
    def insert_company(self):   
        try:
            params = self.company
            params.update({"SystemToken" : self._connector._SystemToken})
            res = requests.post(self._connector.ResourceCatalog_url + "/insertCompany", params=params, 
                                    data= json.dumps(self.adminInfo))
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
                    print(f"Denied by the Resource Catalog\n")
                    return False
            except:
                print(f"Error in the information\n")
                return False

class RegisterNewUser():
    def __init__(self, chatID, sender, ResourceCatalog_url):
        self.chatID = chatID
        self.ResourceCatalog_url = ResourceCatalog_url
        self._bot = sender
        self._status = 0
        self._completed = False
        self.response = {}
        
        self.update("")

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
            CompanyName = message



    def insert_user(self):
        try:
            res = requests.post(self.ResourceCatalog_url + f"""/insert/user""", params=self.company, json=self.UserInfo)
            res.raise_for_status()
        except :
            print(f"Error in the connection with the Resource Catalog\n")
            return False
        else:
            try:
                res_dict = res.json()
                if res_dict["Status"] == "OK":
                    UserID = res_dict["ID"]
                    message = (f"""User {self.completeName} registered in company {self.company["CompanyName"]}\n"""
                            "Welcome to IoTomatoes Platform\n\n"
                            f"UserID: {UserID}\n")
                    self._bot.sendMessage(message)
                    return True
                elif res_dict["Status"] == "CompanyToken not valid":
                    self._bot.sendMessage("CompanyToken not valid\n")
                    return False
            except:
                print(f"Error in the information\n")
                return False

class GetUsers():
    def __init__(self) -> None:
        pass

class GetDevices():
    def __init__(self) -> None:
        pass

class DeleteCompany():
    def __init__(self) -> None:
        pass