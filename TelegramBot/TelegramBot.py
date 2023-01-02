import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import requests
import sys

sys.path.append("../GenericClasses/")
from MyMQTT import *
from customExceptions import *
from GenericEndPoints import GenericService, GenericMQTTResource
from ItemInfo import ServiceInfo

HelpMessage = ("Welcome to the IoTBot!\n")

class InsertNewCompany():
    def __init__(self, chatID, bot):
        self.chatID = chatID
        self.bot = bot
        self.status = 0
        self.request = {"CompanyName" : "", "Name" : "", "Surname" : ""}
        self.update("")

    @property
    def adminInfo(self):
        return {"Name" : self.request["Name"], "Surname" : self.request["Surname"], "telegramID" : self.chatID}

    @property
    def company(self):
        return {"CompanyName": self.request["CompanyName"]}

    @property
    def chatID(self):
        return self.chatID

    @chatID.setter
    def chatID(self, chatID):
        self.chatID = chatID

    def update(self, message, ResourceCatalog_url = ""): 
        if self.status == len(self.request):
            if len(ResourceCatalog_url) > 0:
                return self.insert_company(ResourceCatalog_url)
            else:
                return False

        if self.status > 0:
            actualKey = list(self.request.keys())[self.status]
            self.request[actualKey] = message
        self.status += 1
        self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self.status]}")
        return None
    
    def insert_company(self, ResourceCatalog_url):   
        try:
            res = requests.post(ResourceCatalog_url + "/insertCompany", 
                                    params=self.company, json=self.adminInfo)
            res.raise_for_status()
        except :
            print(f"Error in the connection with the Resource Catalog\n")
            return False
        else:
            try:
                res_dict = res.json()
                if res_dict["Status"] == "OK":
                    CompanyID = res_dict["companyID"]
                    CompanyToken = res_dict["companyToken"]
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
    def __init__(self, chatID, bot):
        self.chatID = chatID
        self.bot = bot
        self.status = 0
        self.request = {"CompanyName" : "", "Name" : "", "Surname" : "", "CompanyToken" : ""}
        self.update("")

    @property
    def adminInfo(self):
        return {"Name" : self.request["Name"], "Surname" : self.request["Surname"], "telegramID" : self.chatID}

    @property
    def completeName(self):
        return f"{self.adminInfo['Name']} {self.adminInfo['Surname']}"

    @property
    def company(self):
        return {"CompanyName": self.request["CompanyName"], "CompanyToken" : self.request["CompanyToken"]}

    @property
    def chatID(self):
        return self.chatID

    @chatID.setter
    def chatID(self, chatID):
        self.chatID = chatID

    def update(self, message, companyList = [], ResourceCatalog_url = ""): 
        if self.status == len(self.request):
            if len(ResourceCatalog_url) > 0:
                return self.insert_user(ResourceCatalog_url)
            else:
                return False

        if self.status == 0:
            self.status += 1
            if companyList != []:
                buttons = [InlineKeyboardButton(text=company, callback_data=company) for company in companyList]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self.status]}", reply_markup=keyboard)
            else:
                self.bot.sendMessage(self.chatID, "No company registered yet")
                return True
        else:
            actualKey = list(self.request.keys())[self.status]
            self.request[actualKey] = message
            self.status += 1
            self.bot.sendMessage(self.chatID, f"Insert your {list(self.request.keys())[self.status]}")
        return False

    def insert_user(self, ResourceCatalog_url):
        try:
            res = requests.post(ResourceCatalog_url + f"""/insert/user""", 
                                    params=self.company, json=self.adminInfo)
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
                elif res_dict["Status"] == "TokenError":
                    self.bot.sendMessage(self.chatID, text="CompanyToken not valid\n")

                    return False
            except:
                print(f"Error in the information\n")
                return False


class IoTBot(GenericService, GenericMQTTResource):
    def __init__(self, ServiceInfo : ServiceInfo, ServiceCatalog_url):
        super().__init__(ServiceInfo, ServiceCatalog_url)
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()

        #MQTT client
        self.MQTTclient_start()
        self.__message = {'bn': "", 'e': [{'n': "",'v': "", 'u': "", 't': ""}]}
        #TelegramBot
        self.tokenBot = self.get_token()
        self.bot = telepot.Bot(self.tokenBot)
        
        self.chatID = {
            "insert_new_company" : [],
            "register_new_user" : []
        }
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
        if message[1] == "/":
            if message == "/start":
                self.bot.sendMessage(chat_ID, text=HelpMessage)
            elif message == "/insert_new_company":
                self.chatID["insert_new_company"].append(InsertNewCompany(chat_ID, self.bot))
            elif message == "/register_new_user":
                self.chatID["register_new_user"].append(RegisterNewUser(chat_ID, self.bot))
            else:
                self.bot.sendMessage(chat_ID, text="Command not found")
        
        else:
            for chat in self.chatID["insert_new_company"]:
                if chat.ID == chat_ID:
                    if chat.update(chat, message, self.ServiceCatalog_url):
                        self.chatID["insert_new_company"].remove(chat)
                        return
                    
            for chat in self.chatID["register_new_user"]:
                if chat.ID == chat_ID:
                    if chat.update(chat, message, self.companyList, self.ServiceCatalog_url):
                        self.chatID["register_new_user"].remove(chat)
                        return

            else:
                self.bot.sendMessage(chat_ID, text="Command not found")

    def on_callback_query(self,msg):
        _ , chat_ID , query_data = telepot.glance(msg,flavor='callback_query') # type: ignore
        
        for chat in self.chatID["register_new_user"]:
            if chat.ID == chat_ID:
                chat.update(chat, query_data)
        
        self.bot.sendMessage(chat_ID, text="No company selected")

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

    sb = IoTBot(BotInfo, ServiceCatalog_url)

    while True:
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            break

    sb.client.stop()