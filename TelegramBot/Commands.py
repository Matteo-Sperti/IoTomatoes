import json
import requests
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

class InsertNewCompany():
    def __init__(self, chatID, bot, ResourceCatalog_url, companyList):
        self.chatID = chatID
        self.completed = False
        self.ResourceCatalog_url = ResourceCatalog_url
        self.companyList = companyList
        self.bot = bot
        self._status = 0
        self._coordSTD = 44.969741, 7.464239

        self.request = {"CompanyName" : "", "Name" : "", "Surname" : "", 
                            "CompanyToken" : "", "CompanyLocation" : ""}
        self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[0]}")

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, InsertNewCompany):
            return self.chatID == __o.chatID
        return False

    @property
    def adminInfo(self):
        return {"Name" : self.request["Name"], "Surname" : self.request["Surname"], "telegramID" : self.chatID}

    @property
    def company(self):
        return {"CompanyName": self.request["CompanyName"], "CompanyToken": self.request["CompanyToken"]}

    def update(self, message): 
        if self._status < len(self.request):
            actualKey = list(self.request.keys())[self._status]
            print(message)
            self.request[actualKey] = message
            self._status += 1
            if self._status < len(self.request):
                self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self._status]}")
                if self._status == len(self.request) - 1:
                    self.bot.sendMessage(self.chatID, "Insert your location:")
                    self.bot.sendLocation(self.chatID, self._coordSTD)
            else:
                question = f"Your Token is {message}\nConfirm your registration?"
                buttons = buttons = [[InlineKeyboardButton(text=f'YES ✅', callback_data='yes'), 
                        InlineKeyboardButton(text=f'NO ❌', callback_data='no')]]
                keyboards = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(self.chatID, question, reply_markup=keyboards)
                self._status += 1
        else:
            if message == "yes":
                if not self.insert_company():
                    self.bot.sendMessage(self.chatID, "Registration failed")
                else:
                    self.companyList.append(self.company["CompanyName"])
            else:
                self.bot.sendMessage(self.chatID, "Registration canceled")
            self.completed = True
            
    def insert_company(self):   
        try:
            res = requests.post(self.ResourceCatalog_url + "/insertCompany", params=self.company, data= json.dumps(self.adminInfo))
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
                    self.bot.sendMessage(self.chatID, text=message)
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