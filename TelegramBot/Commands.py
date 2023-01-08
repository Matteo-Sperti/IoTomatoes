import json
import requests
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

keyboardYESNO = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='YES ✅', callback_data='yes'),
                InlineKeyboardButton(text='NO ❌', callback_data='no'),
            ]])

class InsertNewCompany():
    def __init__(self, chatID, sender, ResourceCatalog_url):
        self.chatID = chatID
        self.completed = False
        self.ResourceCatalog_url = ResourceCatalog_url
        self.sender = sender
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
                "CompanyToken": self.response["CompanyToken"]}

    @property
    def location(self):
        return self.response["Location"]

    def update(self, message): 
        if self._status == 0:
            self.sender.sendMessage("Insert your Company Name")
            self._status += 1
        
        elif self._status == 1:
            self.response["CompanyName"] = message
            self.sender.sendMessage("Insert your Name")
            self._status += 1

        elif self._status == 2:
            self.response["Name"] = message
            self.sender.sendMessage("Insert your Surname")
            self._status += 1
        
        elif self._status == 3:
            self.response["Surname"] = message
            self.sender.sendMessage("Insert your Company Token")
            self._status += 1

        elif self._status == 4:
            self.response["CompanyToken"] = message
            self.sender.sendMessage(f"Your Company Token is: {message}\nProceed with the registration?",
                                    reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 5:
            if message == "yes":
                self.sender.sendMessage("Insert your location as couple of coordinates:")
                self._status += 1
            else:
                self.sender.sendMessage("Insert your Company Token")
                self._status = 4

        elif self._status == 6:
            try:
                message.replace(" ", "")
                latitude, longitude = message.split(",")
                self.response["Location"] = {
                    "longitude" : float(longitude),
                    "latitude" : float(latitude)
                }           
                self.sender.sendLocation(self.location["latitude"], self.location["longitude"])
            except:
                self.sender.sendMessage("Invalid location")
                self.sender.sendMessage("Insert your location as couple of coordinates:")
                self._status = 6
            else:
                self.sender.sendMessage(f"Is this your location?", reply_markup=keyboardYESNO)
                self._status += 1

        elif self._status == 7:
            if message == "yes":
                summary = (f"You are going to register the following company:\n"
                            f"Company Name: {self.response['CompanyName']}\n"
                            f"Company Token: {self.response['CompanyToken']}\n"
                            f"Location: {self.location['latitude']}, {self.location['longitude']}\n\n"
                            f"{self.response['Name']} {self.response['Surname']}) will be the admin of this company\n")
                self.sender.sendMessage(summary)
                self.sender.sendMessage("Confirm your registration?", reply_markup=keyboardYESNO)
                self._status += 1
            else:
                self.sender.sendMessage("Insert your location as couple coordinates:")
                self._status = 6

        elif self._status == 8:
            if message == "yes":
                if not self.insert_company():
                    self.sender.sendMessage("Registration failed")
                else:
                    self.sender.sendMessage("Registration completed")
            else:
                self.sender.sendMessage("Registration canceled")
            self.completed = True
            
    def insert_company(self):   
        try:
            res = requests.post(self.ResourceCatalog_url + "/insertCompany", params=self.company, 
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
                    self.sender.sendMessage(self.chatID, text=message)
                    return True
            except:
                print(f"Error in the information\n")
                return False

class RegisterNewUser():
    def __init__(self, chatID, bot, ResourceCatalog_url, companyList = []):
        self.chatID = chatID
        self.completed = False
        self.ResourceCatalog_url = ResourceCatalog_url
        self.bot = bot
        self.status = 0
        self.request = {"CompanyName" : "", "Name" : "", "Surname" : "", "CompanyToken" : ""}
        
        if companyList != []:
            buttons = [InlineKeyboardButton(text=company, callback_data=company) for company in companyList]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[0]}", reply_markup=keyboard)

    @property
    def adminInfo(self):
        return {"Name" : self.request["Name"], "Surname" : self.request["Surname"], "telegramID" : self.chatID}

    @property
    def completeName(self):
        return f"{self.adminInfo['Name']} {self.adminInfo['Surname']}"

    @property
    def company(self):
        return {"CompanyName": self.request["CompanyName"], "CompanyToken" : self.request["CompanyToken"]}

    def update(self, message):            
        if self.status < len(self.request):
            actualKey = list(self.request.keys())[self.status]
            self.request[actualKey] = message
            self.status += 1
            if self.status < len(self.request):
                self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self.status]}")
            else:
                question = (f"Your name is {self.completeName}\n"
                            f"Company: {self.company['CompanyName']}\n"
                            f"CompanyToke:{message}\n\n"
                            "Confirm your registration?")
                buttons = buttons = [[InlineKeyboardButton(text=f'YES ✅', callback_data='yes'), 
                        InlineKeyboardButton(text=f'NO ❌', callback_data='no')]]
                keyboards = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(self.chatID, question, reply_markup=keyboards)
                self.status += 1
        else:
            if message == "yes":
                if not self.insert_user():
                    self.bot.sendMessage(self.chatID, "Registration failed")
            else:
                self.bot.sendMessage(self.chatID, "Registration canceled")
            self.completed = True

    def insert_user(self):
        try:
            res = requests.post(self.ResourceCatalog_url + f"""/insert/user""", params=self.company, json=self.adminInfo)
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
                    self.bot.sendMessage(self.chatID, text=message)
                    return True
                elif res_dict["Status"] == "CompanyToken not valid":
                    self.bot.sendMessage(self.chatID, text="CompanyToken not valid\n")
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