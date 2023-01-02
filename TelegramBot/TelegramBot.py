import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import requests
from GenericClasses.MyMQTT import *
from GenericClasses.customExceptions import *
from GenericClasses.GenericEndPoints import GenericMQTTResource, RefreshThread, register
from GenericClasses.ItemInfo import UserInfo

HelpMessage = ("Welcome to the IoTBot!\n")

class IoTBot(GenericMQTTResource):
    def __init__(self, info : UserInfo, ServiceCatalog_url):
        self.ServiceCatalog_url = ServiceCatalog_url
        self.ResourceCatalog_url = self.get_ResourceCatalog_url()
        self.info = info
        #MQTT client
        self.MQTTclient_start()
        #TelegramBot
        self.tokenBot = self.get_token()
        self.bot = telepot.Bot(self.tokenBot)
        
        self.__message = {'bn': "telegramBot",
                          'e':
                          [
                              {'n': 'switch', 'v': '', 't': '', 'u': 'bool'},
                          ]
                          }
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

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text']
        if message == "/start":
            self.bot.sendMessage(chat_ID, text=HelpMessage)

    def notify(self, topic, msg):
        try:
            msg_dict = json.loads(msg)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_dict["timestamp"]))
            message = (f"Alert from {msg_dict['bn']} at {timestamp}:\n"
                    f"ALERT : {msg_dict['alert']}.\n"
                    f"DO: {msg_dict['action']}")
        except KeyError:
            print("Invalid message")
        else:
            if self.chat_ID != 0:
                self.bot.sendMessage(self.chat_ID, text=message)
                print("Message sent to TelegramBot")

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text']
        if message == "/switch":
            buttons = [[InlineKeyboardButton(text=f'ON 🟡', callback_data=f'on'), 
                    InlineKeyboardButton(text=f'OFF ⚪', callback_data=f'off')]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            self.bot.sendMessage(chat_ID, text='What do you want to do', reply_markup=keyboard)
        else:
            self.bot.sendMessage(chat_ID, text="Command not supported")

    def on_callback_query(self,msg):
        query_ID , chat_ID , query_data = telepot.glance(msg,flavor='callback_query')

        
        payload = self.__message.copy()
        payload['e'][0]['v'] = query_data
        payload['e'][0]['t'] = time.time()
        self.client.myPublish(self.topic, payload)
        self.bot.sendMessage(chat_ID, text=f"Led switched {query_data}")

if __name__ == "__main__":
    conf = json.load(open("TelegramSettings.json"))

    # MyAlertBot    
    sb = IoTBot(conf["UserInfo"], conf["ServiceCatalog_url"])


    sb = IoTBot()

    while True:
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            break

    sb.client.stop()