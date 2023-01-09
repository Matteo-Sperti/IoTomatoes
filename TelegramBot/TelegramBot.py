import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.delegate import (
    per_chat_id_in, create_open, pave_event_space, call,
    include_callback_query_chat_id)
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
    def __init__(self, seed_tuple, connector, **kwargs):
        super(MessageHandler, self).__init__(seed_tuple, **kwargs)
        self._connector = connector
        self.command = None

    def on_chat_message(self, msg):
        content_type, _, chat_ID = telepot.glance(msg)  # type: ignore
        
        if content_type != 'text':
            self.sender.sendMessage("I don't understand") 
            return

        message = msg['text']
        if self.command is not None:
            completed = self.command.update(message)
            if completed:
                self.close()
        elif message in ["/help", "/start"]:
            self.bot.sendMessage(chat_ID, text=HelpMessage)
        elif message == "/insert_company":
            self.command = InsertNewCompany(chat_ID, self.sender, self._connector)
        elif message == "/register_user":
            self.command = RegisterNewUser(chat_ID, self.sender, self._connector)
        elif message == "/users":
            self.command = GetUsers(chat_ID, self.sender, self._connector)
        elif message == "/devices":
            self.command = GetDevices(chat_ID, self.sender, self._connector)
        elif message == "/delete_company":
            self.command = DeleteCompany(chat_ID, self.sender, self._connector)
        else:
            self.sender.sendMessage("Command not found")

    def on_callback_query(self,msg):
        _ , chat_ID , query_data = telepot.glance(msg,flavor='callback_query')

        if self.command is not None:
            completed = self.command.update(query_data)
            if completed:
                self.close()
        else:
            self.sender.sendMessage("Command not found")

    def on__idle(self, event):
        self.sender.sendMessage("You have been idle for too long. Closing section.")
        self.close()

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
    def __init__(self, token, connector):
        self._seen = set()
        self._companyList = []
        self._connector = connector

        super(ChatBox, self).__init__(token, [
            # Distribute all messages to all chat_ids, via `per_chat_id_in()`.
            include_callback_query_chat_id(
                pave_event_space())(
                    per_chat_id_in(self._seen, types='private'), create_open, MessageHandler, 
                                    self._connector, timeout=60),

            # For senders never seen before, send him a welcome message.
            (self._is_newcomer, custom_thread(call(self._send_welcome))),
        ])

    # seed-calculating function: use returned value to indicate whether to spawn a delegate
    def _is_newcomer(self, msg):
        if telepot.is_event(msg):
            return None

        if "chat" not in msg:
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
        self.bot = ChatBox(self.tokenBot, self)

        MessageLoop(self.bot).run_as_thread()

    def get_token(self):
        while True:
            try:
                params = {"SystemToken": self._SystemToken}
                res = requests.get(self.ServiceCatalog_url + "/telegram", params=params)
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

    def get_CompanyName_list(self):
        try:
            response = requests.get(self.ResourceCatalog_url + "/companiesName", 
                                        params={"SystemToken": self._SystemToken})
            response.raise_for_status()
            out = response.json()
        except:
            raise ConnectionError("Unable to connect to the Resource Catalog")
        else:
            return out
    
    def get_chatID(self, CompanyName : str) :
        try : 
            params = {"SystemToken": self._SystemToken, "CompanyName": CompanyName}
            res = requests.get(self.ResourceCatalog_url + "users", params=params)
            res.raise_for_status()
        except:
            print("Connection Error\nImpossibile to reach the ResourceCatalog")
            return 0
        else:
            for user in res.json():
                if user["chatID"] != 0:
                    return user["chatID"]
            return 0

    def notify(self, topic, msg):
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg["timestamp"]))
            message = (f"Alert from {msg['bn']} at {timestamp}:\n"
                    f"ALERT : {msg['alert']}.\n"
                    f"DO: {msg['action']}")
            chat_ID = self.get_chatID(msg["bn"])
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
        time.sleep(1)
        print("IoTBot started")

        while True:
            try:
                time.sleep(3)
            except KeyboardInterrupt:
                break

        IoTomatoesBOT.stop()