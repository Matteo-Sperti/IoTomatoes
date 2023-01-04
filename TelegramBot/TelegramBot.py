import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import requests
import sys

from Commands import *
sys.path.append("../SupportClasses/")
from MyExceptions import *
from GenericEndpoint import GenericEndpoint

HelpMessage = """Welcome to the IoTomatoesBot!

This bot will help you to manage your IoT devices for your company.

To start, you need to register your company and your admin account.

To register your company, type /insert_company.
Then you can add your devices and users.

/register_user to add a new user to your company.
/users to see all the users of your company.
/devices to see all the active devices of your company.
"""

class IoTBot(GenericEndpoint):
    def __init__(self, settings :dict):
        super().__init__(settings, isService=True)
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()

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
    settings = json.load(open("TelegramSettings.json"))

    try:
        IoTomatoesBOT = IoTBot(settings)
    except:
        print("Error in the initialization of the IoTBot")
    else:
        print("IoTBot started")
        IoTomatoesBOT.start()
        while True:
            try:
                time.sleep(3)
            except KeyboardInterrupt:
                break

        IoTomatoesBOT.stop()