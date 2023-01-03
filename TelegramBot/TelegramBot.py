import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import requests
import sys

sys.path.append("../SupportClasses/")
from MyExceptions import *
from GenericEndPoints import GenericService, GenericMQTTResource, GenericMQTTEndpoint
from ItemInfo import ServiceInfo

HelpMessage = """Welcome to the IoTomatoesBot!

This bot will help you to manage your IoT devices for your company.

To start, you need to register your company and your admin account.

To register your company, type /insert_company.
Then you can add your devices and users.

/register_user to add a new user to your company.
/users to see all the users of your company.
/devices to see all the active devices of your company.
"""

class InsertNewCompany():
    def __init__(self, chatID, bot, ResourceCatalog_url, companyList):
        self.chatID = chatID
        self.completed = False
        self.ResourceCatalog_url = ResourceCatalog_url
        self.companyList = companyList
        self.bot = bot
        self.status = 0

        self.request = {"CompanyName" : "", "Name" : "", "Surname" : "", "CompanyToken" : ""}
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
        if self.status < len(self.request):
            actualKey = list(self.request.keys())[self.status]
            self.request[actualKey] = message
            self.status += 1
            if self.status < len(self.request):
                self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self.status]}")
            else:
                question = f"Your Token is {message}\nConfirm your registration?"
                buttons = buttons = [[InlineKeyboardButton(text=f'YES ✅', callback_data='yes'), 
                        InlineKeyboardButton(text=f'NO ❌', callback_data='no')]]
                keyboards = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(self.chatID, question, reply_markup=keyboards)
                self.status += 1
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
                print(res)
                res_dict = res.json()
                print(res_dict)
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


class IoTBot(GenericService, GenericMQTTResource):
    def __init__(self, ServiceInfo : ServiceInfo, ServiceCatalog_url):
        super().__init__(ServiceInfo, ServiceCatalog_url)
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()

        #MQTT client
        self.client = GenericMQTTEndpoint(f"IoTomatoes_ID{self.ID}",self.ServiceCatalog_url, self)
        self.__message = {'bn': "", 'e': [{'n': "",'v': "", 'u': "", 't': ""}]}
        #TelegramBot
        self.tokenBot = self.get_token()
        self.bot = telepot.Bot(self.tokenBot)
        
        self.chat_active_list = []
        self.companyList = []

        MessageLoop(self.bot, {'chat': self.on_chat_message,
                               'callback_query': self.on_callback_query}).run_as_thread()
    
    def get_token(self):
        while True:
            try:
                res = requests.get(self.ServiceCatalog_url + "/telegram")
                res.raise_for_status()
            except :
                print(f"Error in the connection with the Service Catalog\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    token = res.json()
                    return token["telegramToken"]
                except KeyError:
                    print(f"Error in the broker information\nRetrying connection\n")
                    time.sleep(1)

    def get_chat_ID(self, ID):
        pass

    def get_companyID(self, chatID):
        pass

    def on_chat_message(self, msg):
        _, _, chat_ID = telepot.glance(msg)  # type: ignore
        
        message = msg['text']
        if message == "/start" or message == "/help":
            self.bot.sendMessage(chat_ID, text=HelpMessage)
        elif message == "/insert_company":
            self.chat_active_list.append(InsertNewCompany(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
        elif message == "/register_user":
            if self.companyList == []:
                self.bot.sendMessage(chat_ID, text="No company registered")
            else:
                self.chat_active_list.append(RegisterNewUser(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
        elif message == "/users":
            pass
        elif message == "/devices":
            pass
        else:
            for chat in self.chat_active_list:
                if chat.chatID == chat_ID:
                    chat.update(message) 
                    if chat.completed:
                        self.chat_active_list.remove(chat)                                          
                    return
            self.bot.sendMessage(chat_ID, text="Command not found")

    def on_callback_query(self,msg):
        _ , chat_ID , query_data = telepot.glance(msg,flavor='callback_query') # type: ignore

        for chat in self.chat_active_list:
            if chat.chatID == chat_ID:
                chat.update(query_data)
                if chat.completed:
                    self.chat_active_list.remove(chat)
                return        
        self.bot.sendMessage(chat_ID, text="Error\nThis chat is not active")

    def notify(self, topic, msg):
        try:
            msg_dict = json.loads(msg)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_dict["timestamp"]))
            message = (f"Alert from {msg_dict['bn']} at {timestamp}:\n"
                    f"ALERT : {msg_dict['alert']}.\n"
                    f"DO: {msg_dict['action']}")
            chat_ID = self.get_chat_ID(msg_dict["bn"])
        except KeyError:
            print("Invalid message")
        else:
            if chat_ID != 0:
                self.bot.sendMessage(chat_ID, text=message)
                print("Message sent to TelegramBot")


if __name__ == "__main__":
    conf = json.load(open("TelegramSettings.json"))

    ServiceCatalog_url = conf["ServiceCatalog_url"]
    BotInfo = ServiceInfo(conf["ServiceName"], IPport=conf["IPport"])

    IoTomatoesBOT = IoTBot(BotInfo, ServiceCatalog_url)

    while True:
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            break

    IoTomatoesBOT.client.stop()