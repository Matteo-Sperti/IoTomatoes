import telepot
from telepot.loop import MessageLoop
from telepot.delegate import (
    per_chat_id_in, create_open, pave_event_space, call,
    include_callback_query_chat_id)
import json
import time
import requests
import signal

from Commands import *
from iotomatoes_supportpackage import BaseService
from iotomatoes_supportpackage.MyThread import SimpleThread

HelpMessage = """Help message to the IoTomatoesBot!

This bot will help you to manage your IoT devices for your company.

You are currently registered in the company {0}.

You can use the following commands:
/users to see all the users of your company.
/devices to see all the active devices of your company.
/fields to see all the fields of your company.
/change_plant to change the plant of your company.
/delete_company to delete your company and all the data related to it.
/plot to require a custom plot of your data.
/position to retrieve the position of your devices.
/trace to retrieve the trace of one of your truck.
/help to see this message again.
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
        """Construct a new MessageHandler instance. 
        It will be used to handle the received messages on a per-chat basis.
        """
        super(MessageHandler, self).__init__(seed_tuple, **kwargs)
        self._connector = connector
        self._command = None

        try:
            self._chat_id = seed_tuple[1]['chat']['id']
        except:
            self._chat_id = 0

        self._CompanyName = self._connector.isRegistered(self._chat_id)

    def on_chat_message(self, msg):
        """Handle the received message"""

        content_type, _, chat_ID = telepot.glance(msg)  # type: ignore

        if content_type != 'text':
            self.sender.sendMessage("I don't understand non-text messages.")
            return

        message = msg['text']
        if self._command is None:
            if self._CompanyName == "":
                if message == "/insert_company":
                    self._command = InsertNewCompany(
                        chat_ID, self.sender, self._connector)
                elif message == "/register_user":
                    self._command = RegisterNewUser(
                        chat_ID, self.sender, self._connector)
                elif message in ["/help", "/start"]:
                    self.sender.sendMessage(WelcomeMessage)
                else:
                    self.sender.sendMessage(
                        "You need to register your company first "
                        "or register yourself in an existing company.\n"
                        "Type /insert_company to register your company or /help for more info.")
            else:
                if message == "/users":
                    getUsers(self._CompanyName, self.sender, self._connector)
                elif message == "/devices":
                    getDevices(self._CompanyName, self.sender, self._connector)
                elif message == "/fields":
                    getFields(self._CompanyName, self.sender, self._connector)
                elif message == "/delete_company":
                    self._command = DeleteCompany(
                        self._CompanyName, self._chat_id, self.sender, self._connector)
                elif message in ["/help", "/start"]:
                    self.sender.sendMessage(
                        HelpMessage.format(self._CompanyName))
                elif message == "/change_plant":
                    self._command = ChangePlant(
                        self._CompanyName, self.sender, self._connector)
                elif message == "/plot":
                    self._command = CustomPlot(
                        self._CompanyName, self.sender, self._connector)
                elif message == "/position":
                    self._command = GetPosition(
                        self._CompanyName, self.sender, self._connector)
                elif message == "/trace":
                    self._command = Trace(
                        self._CompanyName, self.sender, self._connector)
                else:
                    self.sender.sendMessage(f"Command not found or not permitted.\n"
                                            f"Type /help for more info.")

        if self._command is not None:
            completed = self._command.update(message)
            if completed:
                self.close()
        else:
            self.close()

    def on_callback_query(self, msg):
        """Handle the callback query"""

        _, chat_ID, query_data = telepot.glance(msg, flavor='callback_query')

        if self._command is not None:
            completed = self._command.update(query_data)
            if completed:
                self.close()
        else:
            self.sender.sendMessage("Command not found")

    def on__idle(self, event):
        """Close the delegate if the user is idle for too long"""

        self.sender.sendMessage(
            "You have been idle for too long. Closing section.")
        self.close()

    def on_close(self, ex):
        """Close the delegate and reset the command"""

        self._command = None
        print("Closing delegate")


class ChatBox(telepot.DelegatorBot):
    def __init__(self, token: str, connector):
        """Initialize the delegator bot.

        Arguments:
        - `token (str)`: the token of the bot
        - `connector`: the endpoint object uses to connect to other services
        """

        self._seen = set()
        self._companyList = []
        self._connector = connector

        super(ChatBox, self).__init__(token, [
            # Distribute all messages to all chat_ids, via `per_chat_id_in()`.
            include_callback_query_chat_id(
                pave_event_space())(
                    per_chat_id_in(
                        self._seen, types='private'), create_open, MessageHandler,
                self._connector, timeout=300),

            # For senders never seen before, send him a welcome message.
            (self._is_newcomer, custom_thread(call(self._send_welcome))),
        ])

    # seed-calculating function: use returned value to indicate whether to spawn a delegate
    def _is_newcomer(self, msg):
        """Check if the sender is a newcomer"""

        if telepot.is_event(msg):
            return None

        if "chat" not in msg:
            return None

        chat_id = msg['chat']['id']
        if chat_id in self._seen:  # Sender has been seen before
            return None  # No delegate spawned

        self._seen.add(chat_id)
        # non-hashable ==> delegates are independent, no seed association is made.
        return []

    def _send_welcome(self, seed_tuple):
        """Send a welcome message to new users"""

        chat_id = seed_tuple[1]['chat']['id']
        self.sendMessage(chat_id, WelcomeMessage)


class IoTBot(BaseService):
    def __init__(self, settings: dict):
        """Initialize the IoTBot service"""

        super().__init__(settings)

        self._message = {'bn': "", 'e': [{'n': "", 'v': "", 'u': "", 't': ""}]}
        # TelegramBot
        self.tokenBot = self.get_token()
        self.bot = ChatBox(self.tokenBot, self)
        self.DataVisualizer = settings["DataVisualizer_Service"]
        self.Database = settings["Database_Service"]
        self.Localization = settings["Localization_Service"]
        MessageLoop(self.bot).run_as_thread()

    def get_token(self):
        """Return the telegram token from the Service Catalog"""

        while True:
            try:
                res = requests.get(self._ServiceCatalog_url + "/telegram")
                res.raise_for_status()
            except:
                print(
                    f"Error in the connection with the Service Catalog\nRetrying connection\n")
                time.sleep(1)
            else:
                try:
                    token = res.json()
                    return token["telegramToken"]
                except KeyError:
                    print(f"Error in the broker information\nRetrying connection\n")
                    time.sleep(1)

    def isRegistered(self, chatID: int):
        """Return the name of the company if the chatID is already registered.
        Otherwise return an empty string.

        Arguments:
        - `chatID (int)`: telegramID of the user
        """
        try:
            params = {"telegramID": chatID}
            res = requests.get(self.ResourceCatalog_url +
                               "/isRegistered", params=params)
            res.raise_for_status()
        except:
            print("Connection Error\nImpossibile to reach the ResourceCatalog")
            return ""
        else:
            res_dict = res.json()
            if "CompanyName" in res_dict and res_dict["CompanyName"] != "":
                return res_dict["CompanyName"]
            else:
                return ""

    def getList(self, CompanyName: str, listType: str):
        """Return the list of users, devices or fields of a company.
        If the list is empty, return an empty list. If an error occurs, return None.

        Arguments:
        - `CompanyName (str)`: name of the company\n
        - `listType (str)`: type of the list to return. It can be "users", "devices" or "fields"
        """
        if listType not in ["users", "devices", "fields"]:
            return None

        try:
            res = requests.get(
                f"{self.ResourceCatalog_url}/{CompanyName}/{listType}")
            res.raise_for_status()
            res_dict = res.json()
        except:
            print("Connection Error\nImpossibile to reach the ResourceCatalog")
            return None
        else:
            if len(res_dict) > 0:
                return res_dict
            else:
                return []

    def notify(self, topic, msg):
        """Notify the user of the message received from the broker"""

        try:
            timestamp = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(msg["t"]))
            message = (f"\nMessage from {msg['bn']} at {timestamp}:\n")
            for key, value in msg.items():
                if key not in ["bn", "t", "cn"]:
                    message += (f"{key}: {value}\n")
        except:
            print("Invalid message")
        else:
            if "telegramID" in msg:
                try:
                    chatID = int(msg["telegramID"])
                    self.bot.sendMessage(chatID, text=message)
                except:
                    print("Invalid chatID")
            else:
                CompanyName = topic.split("/")[0]
                users = self.getList(CompanyName, "users")
                if users is None:
                    print("Error! No users found")
                else:
                    for user in users:
                        try:
                            chatID = int(user["telegramID"])
                            self.bot.sendMessage(chatID, text=message)
                        except:
                            print("Invalid chatID from catalog")


def custom_thread(func):
    def f(seed_tuple):
        target = func(seed_tuple)

        if type(target) is tuple:
            run, args, kwargs = target
            t = SimpleThread(target=run, args=args, kwargs=kwargs)
        else:
            t = SimpleThread(target=target)

        return t
    return f


def sigterm_handler(signal, frame):
    IoTomatoesBOT.stop()
    print("Server stopped")


signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    try:
        settings = json.load(open("TelegramSettings.json"))

        IoTomatoesBOT = IoTBot(settings)
    except Exception as e:
        print(e)
        print("Error in the initialization of the IoTBot")
    else:
        time.sleep(1)
        print("IoTBot started")

        while True:
            time.sleep(5)
