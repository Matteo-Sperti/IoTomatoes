import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.delegate import (
    per_chat_id, create_open, pave_event_space, call)
import json
import time
import requests
import sys
import threading
from socket import gethostname, gethostbyname

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

WelcomeMessage = """Welcome to the IoTomatoesBot!

This bot will help you to manage your IoT devices for your company.

To start, you need to register your company and your admin account.
If your company is already registered, you can register your account to your company.

/insert_company to register your company.
/register_user to register yourself in an existing company.
"""

class MessageHandler(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self._count = 0
        self.obj = None

    def on_chat_message(self, msg):
        content_type, _, chat_ID = telepot.glance(msg)  # type: ignore
        
        if content_type != 'text':
            self.sender.sendMessage(chat_ID, text="I don't understand")
            return

        message = msg['text']
        if message == "/help":
            self.bot.sendMessage(chat_ID, text=HelpMessage)
        elif message == "/insert_company":
            self..append(InsertNewCompany(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
        else:
            for chat in self.chat_active_list:
                if chat.chatID == chat_ID:
                    chat.update(message) 
                    if chat.completed:
                        self.chat_active_list.remove(chat)                                          
                    return

            if self.companyList == []:
                self.bot.sendMessage(chat_ID, text="Error, no company registered")
            else:
                if message == "/register_user":
                    self.chat_active_list.append(RegisterNewUser(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
                elif message == "/users":
                    self.chat_active_list.append(RegisterNewUser(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
                elif message == "/devices":
                    self.chat_active_list.append(RegisterNewUser(chat_ID, self.bot, self.ResourceCatalog_url, self.companyList))
                else:

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


class CustomThread(threading.Thread):
    def start(self):
        super(CustomThread, self).start()

# Note how this function wraps around the `call()` function below to implement
# a custom thread for delegation.
def custom_thread(func):
    def f(seed_tuple):
        target = func(seed_tuple)

        if type(target) is tuple:
            run, args, kwargs = target
            t = CustomThread(target=run, args=args, kwargs=kwargs)
        else:
            t = CustomThread(target=target)

        return t
    return f


class ChatBox(telepot.DelegatorBot):
    def __init__(self, token,):
        self._seen = set()

        super(ChatBox, self).__init__(token, [
            # Here is a delegate to specially handle owner commands.
            pave_event_space()(
                per_chat_id(types='private'), create_open, MessageHandler, timeout=60),

            # For senders never seen before, send him a welcome message.
            (self._is_newcomer, custom_thread(call(self._send_welcome))),
        ])

    # seed-calculating function: use returned value to indicate whether to spawn a delegate
    def _is_newcomer(self, msg):
        if telepot.is_event(msg):
            return None

        chat_id = msg['chat']['id']
        if chat_id in self._seen:  # Sender has been seen before
            return None  # No delegate spawned

        self._seen.add(chat_id)
        return []  # non-hashable ==> delegates are independent, no seed association is made.

    def _send_welcome(self, seed_tuple):
        chat_id = seed_tuple[1]['chat']['id']
        self.sendMessage(chat_id, WelcomeMessage)


class IoTBot(GenericEndpoint):
    def __init__(self, settings :dict):
        super().__init__(settings, isService=True)

        self._message = {'bn': "", 'e': [{'n': "",'v': "", 'u': "", 't': ""}]}
        #TelegramBot
        self.tokenBot = self.get_token()
        self.bot = ChatBox(self.tokenBot)
        
        self._companyList = []

        MessageLoop(self.bot).run_as_thread()

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

    def notify(self, topic, msg):
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg["timestamp"]))
            message = (f"Alert from {msg['bn']} at {timestamp}:\n"
                    f"ALERT : {msg['alert']}.\n"
                    f"DO: {msg['action']}")
            chat_ID = self.get_chat_ID(msg["bn"])
        except KeyError:
            print("Invalid message")
        else:
            if chat_ID != 0:
                self.bot.sendMessage(chat_ID, text=message)


if __name__ == "__main__":
    settings = json.load(open("TelegramSettings.json"))

    local_IPaddress = gethostbyname(gethostname())
    settings["IPaddress"] = local_IPaddress
    
    try:
        IoTomatoesBOT = IoTBot(settings)
    except Exception as e:
        print(e)
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