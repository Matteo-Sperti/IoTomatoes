import json
import requests
import base64
import datetime
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

keyboardYESNO = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text='YES ✅', callback_data='yes'),
    InlineKeyboardButton(text='NO ❌', callback_data='no'),
]])


class InsertNewCompany():
    def __init__(self, chatID, sender, connector):
        """This class is used to insert a new company in the system.
        It is used by the /insertNewCompany command.

        Arguments:
        - `chatID` : the ID of the chat with the user
        - `sender` : the TelegramBot object
        - `connector` : the IoTBot object used to comunicate with other services.
        """
        self.chatID = chatID
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.response = {}

    @property
    def adminInfo(self):
        return {"Name": self.response["Name"],
                "Surname": self.response["Surname"],
                "telegramID": self.chatID}

    @property
    def company(self):
        return {"CompanyName": self.response["CompanyName"],
                "Location": self.location,
                "NumberOfFields": self.response["NumberOfFields"]}

    @property
    def location(self):
        return self.response["Location"]

    def update(self, message: str):
        """Update the status of the chat.

        Arguments:
        - `message (str)` : the message received from the user.

        Return:
        - `True` if the command is finished,
        - `False` otherwise.
        """
        if self._status == 0:
            self._bot.sendMessage("Insert your Company Name")
            self._status += 1
            return False

        elif self._status == 1:
            if " " in message:
                self._bot.sendMessage(
                    "Invalid Company Name, please do not use spaces")
                self._bot.sendMessage("Insert your Company Name")
                return False
            if message == "admin" or message == "local" or message == "PlantDatabase":
                self._bot.sendMessage(
                    "Invalid Company Name, please do not use 'admin' or 'local' as Company Name")
                self._bot.sendMessage("Insert your Company Name")
                return False
            self.response["CompanyName"] = message
            self._bot.sendMessage("Insert your Name")
            self._status += 1
            return False

        elif self._status == 2:
            self.response["Name"] = message
            self._bot.sendMessage("Insert your Surname")
            self._status += 1
            return False

        elif self._status == 3:
            self.response["Surname"] = message
            self._bot.sendMessage(
                "Insert your location as couple of coordinates:")
            self._status += 1
            return False

        elif self._status == 4:
            try:
                message.replace(" ", "")
                latitude, longitude = message.split(",")
                self.response["Location"] = {
                    "longitude": float(longitude),
                    "latitude": float(latitude)
                }
                self._bot.sendLocation(
                    self.location["latitude"], self.location["longitude"])
            except:
                self._bot.sendMessage("Invalid location")
                self._bot.sendMessage(
                    "Insert your location as couple of coordinates:")
                return False
            else:
                self._bot.sendMessage(
                    f"Is this your location?", reply_markup=keyboardYESNO)
                self._status += 1
                return False

        elif self._status == 5:
            if message == "yes":
                self._bot.sendMessage(
                    "How many indipendent fields do you have in your company?")
                self._status += 1
            else:
                self._bot.sendMessage(
                    "Insert your location as couple coordinates:")
                self._status = 4
            return False

        elif self._status == 6:
            try:
                self.response["NumberOfFields"] = int(message)
            except:
                self._bot.sendMessage(
                    "Invalid number, please insert a positive integer number")
                self._bot.sendMessage(
                    "How many indipendent fields do you have in your company?")
                return False
            else:
                self._bot.sendMessage(
                    "Insert the colture of your fields, separated by a comma")
                self._status += 1
                return False

        elif self._status == 7:
            try:
                fields = message.split(",")
                if len(fields) != self.response["NumberOfFields"]:
                    raise ValueError

                self.response["fieldsList"] = []
                for i, field in enumerate(fields):
                    self.response["fieldsList"].append({
                        "fieldNumber": i+1,
                        "plant": field.lower().strip()
                    })
            except:
                self._bot.sendMessage("Invalid input")
                self._bot.sendMessage(
                    "Insert the colture of your fields, separated by a comma")
                return False
            else:
                summary = (f"You are going to register the following company:\n"
                           f"Company Name: {self.response['CompanyName']}\n"
                           f"Location: {self.location['latitude']}, {self.location['longitude']}\n\n"
                           f"{self.response['Name']} {self.response['Surname']} will be the admin of this company\n")
                self._bot.sendMessage(summary)
                self._bot.sendMessage(
                    "Confirm your registration?", reply_markup=keyboardYESNO)
                self._status += 1
                return False

        elif self._status == 8:
            if message == "yes":
                if self.insert_company():
                    self._bot.sendMessage("Registration completed")
                else:
                    self._bot.sendMessage("Registration failed")
            else:
                self._bot.sendMessage("Registration canceled")
            return True

    def insert_company(self):
        """Insert the company in the Resource Catalog.

        Returns:
        - `True` if the company is correctly inserted in the Resource Catalog.
        - `False` otherwise.
        """
        try:
            body = {"CompanyInfo": self.company,
                    "AdminInfo": self.adminInfo,
                    "fieldsList": self.response["fieldsList"]}
            res = requests.post(self._connector.ResourceCatalog_url + "/company",
                                data=json.dumps(body))
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
                    message = (f"""Company {self.company["CompanyName"]} registered\n"""
                               "Welcome to IoTomatoes Platform\n\n"
                               f"CompanyID: {CompanyID}")
                    self._bot.sendMessage(message)
                    return True
                else:
                    if "Error" in res_dict:
                        if res_dict["Error"] == "Company already registered":
                            self._bot.sendMessage("Company already registered")
                    print(f"Denied by the Resource Catalog\n")
                    return False
            except:
                print(f"Error in the information\n")
                return False


class RegisterNewUser():
    def __init__(self, chatID, sender, connector):
        """This class is used to register a new user in the Resource Catalog.

        Arguments:
        - `chatID` : the telegram ID of the user.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.chatID = chatID
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.response = {}

    @property
    def UserInfo(self):
        return {"Name": self.response["Name"],
                "Surname": self.response["Surname"],
                "telegramID": self.chatID}

    @property
    def completeName(self):
        return f"{self.UserInfo['Name']} {self.UserInfo['Surname']}"

    @property
    def company(self):
        return {"CompanyName": self.response["CompanyName"]}

    def update(self, message):
        """Update the status of the registration.

        Arguments:
        - `message` : the message received from the user.

        Returns:
        - `True` if the registration is completed.
        - `False` otherwise.
        """
        if self._status == 0:
            self._bot.sendMessage("Insert your Company Name")
            self._status += 1
            return False

        elif self._status == 1:
            self.response["CompanyName"] = message
            self._bot.sendMessage("Insert your Name")
            self._status += 1
            return False

        elif self._status == 2:
            self.response["Name"] = message
            self._bot.sendMessage("Insert your Surname")
            self._status += 1
            return False

        elif self._status == 3:
            self.response["Surname"] = message
            summary = (
                f"You are going to register you ({self.completeName})"
                f"as a new user of {self.response['CompanyName']}\n")
            self._bot.sendMessage(
                f"{summary}\nConfirm your registration?", reply_markup=keyboardYESNO)
            self._status += 1
            return False

        elif self._status == 4:
            if message == "yes":
                if self.insert_user():
                    self._bot.sendMessage("Registration completed")
                else:
                    self._bot.sendMessage("Registration failed")
            else:
                self._bot.sendMessage("Registration canceled")
            return True

    def insert_user(self):
        """Insert the user in the Resource Catalog.

        Returns:
        - `True` if the user is correctly inserted in the Resource Catalog.
        - `False` otherwise.
        """
        try:
            res = requests.post(self._connector.ResourceCatalog_url + f"/user",
                                params=self.company, json=self.UserInfo)
            res.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            print(f"Error in the connection with the Resource Catalog\n")
            return False
        else:
            try:
                res_dict = res.json()
                UserID = res_dict["ID"]
                message = (f"""User {self.completeName} registered in company {self.company["CompanyName"]}\n"""
                           "Welcome to IoTomatoes Platform\n\n"
                           f"UserID: {UserID}\n")
                self._bot.sendMessage(message)
                return True
            except:
                print(f"Error in the information\n")
                return False


def getUsers(CompanyName: str, bot, connector) -> None:
    """Get the list of users registered in the Resource Catalog.

    Arguments:
    - `CompanyName (str)` : the name of the company.
    - `bot` : the object used to send messages to the user.
    - `connector` : the IoTBot object used to connect to the Resource Catalog.
    """
    users = connector.getList(CompanyName, "users")
    if users is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(users) == 0:
        bot.sendMessage(f"No users registered in {CompanyName}")
    else:
        message = (f"Users in {CompanyName}:\n\n")
        bot.sendMessage(message)
        for user in users:
            message = (f"Name: {user['Name']}\n"
                       f"Surname: {user['Surname']}\n"
                       f"UserID: {user['ID']}\n\n")
            bot.sendMessage(message)


def getDevices(CompanyName: str, bot, connector) -> None:
    """Get the list of devices registered in the Resource Catalog.

    Arguments:
    - `CompanyName (str)` : the name of the company.
    - `bot` : the object used to send messages to the user.
    - `connector` : the IoTBot object used to connect to the Resource Catalog.
    """
    devices = connector.getList(CompanyName, "devices")
    if devices is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(devices) == 0:
        bot.sendMessage(f"No devices registered in {CompanyName}")
    else:
        message = (f"Devices in {CompanyName}:\n\n")
        bot.sendMessage(message)
        for device in devices:
            message = (f"Device Name: {device['deviceName']}\n"
                       f"DeviceID: {device['ID']}\n"
                       f"Field: {device['fieldNumber']}\n"
                       f"Location: {device['Location']['latitude']}, {device['Location']['longitude']}\n")
            if device["isActuator"]:
                act_msg = f"Actuators: " + \
                    ", ".join(device["actuatorType"])
                message = message + act_msg + "\n"
            if device["isSensor"]:
                sens_msg = f"Sensors: " + ", ".join(device["measureType"])
                message = message + sens_msg + "\n"
            bot.sendMessage(message)


def getFields(CompanyName: str, bot, connector) -> None:
    """Get the list of fields registered in the Resource Catalog.

    Arguments:
    - `CompanyName (str)` : the name of the company.
    - `bot` : the object used to send messages to the user.
    - `connector` : the IoTBot object used to connect to the Resource Catalog.
    """
    fields = connector.getList(CompanyName, "fields")
    if fields is None:
        bot.sendMessage("Error in the connection with the Resource Catalog")
    elif len(fields) == 0:
        bot.sendMessage(f"No fields registered in {CompanyName}")
    else:
        message = (f"Fields in {CompanyName}:\n\n")
        bot.sendMessage(message)
        for field in fields:
            message = (f"Field number: {field['fieldNumber']}\n"
                       f"plant: {field['plant']}\n")
            bot.sendMessage(message)


class DeleteCompany():
    def __init__(self, CompanyName: str, chatID, sender, connector):
        """Delete a company from the Resource Catalog.

        Arguments:
        - `CompanyName (str)` : the name of the company.
        - `chatID (int)` : the chatID of the user.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.chatID = chatID
        self.CompanyName = CompanyName
        self._connector = connector
        self._bot = sender
        self._status = 0

    def update(self, message):
        """Update the status of the deletion.

        Arguments:
        - `message (str)` : the message received from the user.

        Returns:
        - `True` if the deletion is completed.
        - `False` otherwise.
        """

        if self._status == 0:
            self._bot.sendMessage(
                "You are going to delete company " + self.CompanyName)
            self._bot.sendMessage("Confirm your deletion?",
                                  reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 1:
            if message == "yes":
                if self.delete_company():
                    self._bot.sendMessage("Deletion completed")
                else:
                    self._bot.sendMessage("Deletion failed")
            else:
                self._bot.sendMessage("Deletion canceled")
            return True

    def delete_company(self):
        """Delete the company from the Resource Catalog."""

        try:
            params = {"CompanyName": self.CompanyName,
                      "telegramID": self.chatID}
            res = requests.delete(self._connector.ResourceCatalog_url + "/company",
                                  params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            elif err.response.status_code == 403:
                self._bot.sendMessage(
                    "You are not authorized to delete this company.\nContact your administrator.")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            self._bot.sendMessage(
                "Error in the connection with the Resource Catalog")
            return False
        else:
            if "Status" in dict_ and dict_["Status"]:
                return True
            else:
                return False


class ChangePlant():
    def __init__(self, CompanyName: str, sender, connector):
        """Change the plant of a field.

        Arguments:
        - `CompanyName (str)` : the name of the company.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.CompanyName = CompanyName
        self.FieldNumber = ""
        self.newplant = ""
        self._connector = connector
        self._bot = sender
        self._status = 0

    def update(self, message):
        """Update the status of the change.

        Arguments:
        - `message (str)` : the message received from the user.

        Returns:
        - `True` if the procedure is completed.
        - `False` otherwise.
        """

        if self._status == 0:
            fields = self._connector.getList(self.CompanyName, "fields")
            if fields == None:
                self._bot.sendMessage(
                    "Error in the connection with the Resource Catalog")
                return True
            elif len(fields) == 0:
                self._bot.sendMessage("No fields registered")
                return True
            else:
                inline_keyboard_ = []
                for field in fields:
                    number = field['fieldNumber']
                    plant = field['plant']
                    button = InlineKeyboardButton(
                        text=f"Field {number} : {plant}", callback_data=f"{number}")
                    inline_keyboard_.append([button])
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=inline_keyboard_)
                self._bot.sendMessage(f"Which field of company {self.CompanyName} do you want to change?",
                                      reply_markup=keyboard)
                self._status += 1

        elif self._status == 1:
            try:
                self.FieldNumber = int(message)
            except:
                self._bot.sendMessage("Field number must be an integer")
                self._status += 0
            else:
                self._bot.sendMessage("Insert the new plant")
                self._status += 1

        elif self._status == 2:
            self.newplant = message
            change = f"You are changing the plant of field {self.FieldNumber} of company {self.CompanyName} to {self.newplant}"
            self._bot.sendMessage(
                f"{change}\nConfirm your change?", reply_markup=keyboardYESNO)
            self._status += 1

        elif self._status == 3:
            if message == "yes":
                if self.change_plant():
                    self._bot.sendMessage("Update of field completed")
                else:
                    self._bot.sendMessage("Update of field failed")
            else:
                self._bot.sendMessage("Update of field canceled")
            return True

    def change_plant(self):
        """Change the plant of a field in the Resource Catalog."""

        try:
            params = {
                "fieldNumber": self.FieldNumber,
                "plant": self.newplant
            }
            res = requests.put(f"{self._connector.ResourceCatalog_url}/{self.CompanyName}/field",
                               params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Company not registered")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            self._bot.sendMessage(
                "Error in the connection with the Resource Catalog")
            return False
        else:
            if "Status" in dict_ and dict_["Status"]:
                return True
            else:
                return False


class CustomPlot():
    def __init__(self, CompanyName: str, sender, connector):
        """Create a custom plot.

        Arguments:
        - `CompanyName (str)` : the name of the company.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.CompanyName = CompanyName
        self.FieldNumber = -1
        self.Measure = ""
        self.start_date = ""
        self.end_date = ""
        self._connector = connector
        self._bot = sender
        self._status = 0

    def update(self, message):
        """Update the status of the chat.

        Arguments:
        - `message (str)` : the message received from the user.

        Returns:
        - `True` if the procedure is completed.
        - `False` otherwise.
        """

        if self._status == 0:
            self._bot.sendMessage("Insert the measurement you want to plot")
            self._status += 1
            return False

        elif self._status == 1:
            if message == "consumption":
                self.Measure = "consumption"
                self._bot.sendMessage(
                    "Insert the start date (format YYYY-MM-DD)")
                self._status = 3
                return False
            else:
                self.Measure = message
                fields = self._connector.getList(self.CompanyName, "fields")
                if fields == None:
                    self._bot.sendMessage(
                        "Error in the connection with the Resource Catalog")
                    return True
                elif len(fields) == 0:
                    self._bot.sendMessage("No fields registered")
                    return True
                else:
                    inline_keyboard_ = []
                    for field in fields:
                        number = field['fieldNumber']
                        plant = field['plant']
                        button = InlineKeyboardButton(
                            text=f"Field {number} : {plant}", callback_data=f"{number}")
                        inline_keyboard_.append([button])
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=inline_keyboard_)
                    self._bot.sendMessage(f"Choose field of company {self.CompanyName}!",
                                          reply_markup=keyboard)
                    self._status += 1
                    return False

        elif self._status == 2:
            try:
                self.FieldNumber = int(message)
            except:
                self._bot.sendMessage("Field number must be an integer")
                return False
            else:
                self._bot.sendMessage(
                    "Insert the start date (format YYYY-MM-DD)")
                self._status += 1
                return False

        elif self._status == 3:
            try:
                datetime.datetime.strptime(message, '%Y-%m-%d')
            except ValueError:
                self._bot.sendMessage(
                    "Incorrect date format, should be YYYY-MM-DD")
                self._bot.sendMessage(
                    "Insert the start date (format YYYY-MM-DD)")
                return False
            else:
                self.start_date = message
                self._bot.sendMessage(
                    "Insert the end date (format YYYY-MM-DD)")
                self._status += 1
                return False

        elif self._status == 4:
            try:
                datetime.datetime.strptime(message, '%Y-%m-%d')
            except ValueError:
                self._bot.sendMessage(
                    "Incorrect date format, should be YYYY-MM-DD")
                self._bot.sendMessage(
                    "Insert the end date (format YYYY-MM-DD)")
                return False
            else:
                self.end_date = message

                if self.Measure == "consumption":
                    out = self.get_consumption()
                else:
                    out = self.get_plot()

                if not out:
                    self._bot.sendMessage("Error in the creation of the plot")

                return True

        else:
            return True

    def get_plot(self):
        """Get the image of the custom plot from the Data Visualization Service"""

        url = self._connector.getOtherServiceURL(
            self._connector.DataVisualizer)
        if url == None:
            return False

        try:
            params = {
                "Field": self.FieldNumber,
                "measure": self.Measure.lower(),
                "start_date": datetime.datetime.strptime(self.start_date, '%Y-%m-%d').timestamp() - 43200,
                "end_date": datetime.datetime.strptime(self.end_date, '%Y-%m-%d').timestamp() + 43200,
            }
            res = requests.get(f"{url}/{self.CompanyName}/measure",
                               params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Measures not found")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            print(f"Error in the connection with the Data Visualization Service")
            return False
        else:
            if "img64" in dict_:
                fileName = "plot.png"
                binaryString = dict_["img64"].encode("utf-8")
                with open(fileName, "wb") as fh:
                    fh.write(base64.b64decode(binaryString))
                with open(fileName, "rb") as fh:
                    self._bot.sendPhoto(fh)
                return True
            else:
                return False

    def get_consumption(self):
        """Get the image of the consumption plot from the Data Visualization Service"""

        url = self._connector.getOtherServiceURL(
            self._connector.DataVisualizer)

        try:
            params = {
                "start_date": datetime.datetime.strptime(self.start_date, '%Y-%m-%d').timestamp() - 43200,
                "end_date": datetime.datetime.strptime(self.end_date, '%Y-%m-%d').timestamp() + 43200,
            }
            res = requests.get(f"{url}/{self.CompanyName}/consumption",
                               params=params)
            res.raise_for_status()
            dict_ = res.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                self._bot.sendMessage("Measures not found")
            else:
                print(f"{err.response.status_code} : {err.response.reason}")
            return False
        except:
            print(f"Error in the connection with the Data Visualization Service")
            return False
        else:
            if "img64" in dict_:
                fileName = "plot.png"
                binaryString = dict_["img64"].encode("utf-8")
                with open(fileName, "wb") as fh:
                    fh.write(base64.b64decode(binaryString))
                with open(fileName, "rb") as fh:
                    self._bot.sendPhoto(fh)
                return True
            else:
                return False


class GetPosition():
    def __init__(self, CompanyName: str, sender, connector):
        """Get the position of a resource.

        Arguments:
        - `CompanyName (str)` : the name of the company.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.CompanyName = CompanyName
        self.device = None
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.devices = self.getDevices()
        self.trucks = self.getTrucks()

    def getDevices(self):
        """Get the list of devices of the company."""

        listResources = self._connector.getList(self.CompanyName, "devices")
        if listResources == None:
            self._bot.sendMessage(
                "Error in the connection with the Resource Catalog")
            return []
        elif len(listResources) == 0:
            self._bot.sendMessage("No devices registered")
            return []
        else:
            devices = []
            for device in listResources:
                info = {
                    "ID": device["ID"],
                    "deviceName": device["deviceName"],
                    "Location": device["Location"],
                }

                if device["fieldNumber"] != 0:
                    devices.append(info)

            return devices

    def getTrucks(self):
        """Get the last position of the trucks of the company."""

        url = self._connector.getOtherServiceURL(self._connector.Database)
        if url == None:
            self._bot.sendMessage(
                "Error in the connection with the Service Catalog")
            return []

        try:
            res = requests.get(f"{url}/{self.CompanyName}/trucksPosition")
            res.raise_for_status()
            dictTrucks = res.json()
        except:
            self._bot.sendMessage("Error in the connection with the Database")
            return []
        else:
            trucks = []
            for ID, truck in dictTrucks.items():
                info = {
                    "ID": ID,
                    "Location": {
                        "latitude": truck["latitude"],
                        "longitude": truck["longitude"]
                    },
                    "LastUpdate": datetime.datetime.fromtimestamp(truck["t"]).strftime('%Y-%m-%d %H:%M:%S')
                }
                trucks.append(info)

            return trucks

    def update(self, message):
        """Update the status of the chat.

        Arguments:
        - `message (str)` : the message received from the user.

        Returns:
        - `True` if the procedure is completed.
        - `False` otherwise.
        """

        if self._status == 0:
            if self.devices == [] and self.trucks == []:
                self._bot.sendMessage("No devices found")
                return True
            inline_keyboard_ = []
            if self.devices != []:
                button = InlineKeyboardButton(
                    text="Devices", callback_data="Device")
                inline_keyboard_.append([button])
            if self.trucks != []:
                button = InlineKeyboardButton(
                    text="Trucks", callback_data="Truck")
                inline_keyboard_.append([button])

            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard_)
            self._bot.sendMessage("What device do you want to see?",
                                  reply_markup=keyboard)
            self._status += 1
            return False

        elif self._status == 1:
            if message == "Truck":
                if self.trucks == []:
                    self._bot.sendMessage("No trucks registered")
                    return True
                else:
                    inline_keyboard_ = []
                    for device in self.trucks:
                        button = InlineKeyboardButton(
                            text=f"Truck {device['ID']}", callback_data=f"{device['ID']}")
                        inline_keyboard_.append([button])
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=inline_keyboard_)
                    self._bot.sendMessage(f"Choose the Truck of company {self.CompanyName}!",
                                          reply_markup=keyboard)
                    self._status = 21
                    return False
            elif message == "Device":
                if self.devices == []:
                    self._bot.sendMessage("No devices registered")
                    return True
                else:
                    inline_keyboard_ = []
                    for device in self.devices:
                        button = InlineKeyboardButton(
                            text=f"Device {device['ID']} : {device['deviceName']}", callback_data=f"{device['ID']}")
                        inline_keyboard_.append([button])
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=inline_keyboard_)
                    self._bot.sendMessage(f"Choose the Device of company {self.CompanyName}!",
                                          reply_markup=keyboard)
                    self._status = 31
                    return False
            else:
                self._bot.sendMessage("Choose a valid option")
                return False

        elif self._status == 21:
            for device in self.trucks:
                if device["ID"] == message:
                    if device["Location"]["latitude"] == -1 or device["Location"]["longitude"] == -1:
                        self._bot.sendMessage(
                            "No location available for this trucks")
                        return True
                    else:
                        self.device = device
                        self._bot.sendMessage(
                            f"Truck {device['ID']}\nLast update: {device['LastUpdate']}")
                        self._bot.sendLocation(
                            device["Location"]["latitude"], device["Location"]["longitude"])
                        return True

            self._bot.sendMessage("Choose a valid option")
            return False

        elif self._status == 31:
            try:
                DeviceNumber = int(message)
            except:
                self._bot.sendMessage("Device ID must be an integer")
                return False
            else:
                for device in self.devices:
                    if device["ID"] == DeviceNumber:
                        if device["Location"]["latitude"] == -1 or device["Location"]["longitude"] == -1:
                            self._bot.sendMessage(
                                "No location available for this device")
                            return True
                        else:
                            self.device = device
                            self._bot.sendLocation(
                                device["Location"]["latitude"], device["Location"]["longitude"])
                            return True

                self._bot.sendMessage("Choose a valid option")
                return False


class Trace:
    def __init__(self, CompanyName: str, sender, connector):
        """Retrieve the trace of a truck.

        Arguments:
        - `CompanyName (str)` : the name of the company.
        - `sender` : the object used to send messages to the user.
        - `connector` : the IoTBot object used to connect to the Resource Catalog.
        """
        self.CompanyName = CompanyName
        self.device = None
        self._connector = connector
        self._bot = sender
        self._status = 0
        self.trucksIDs = self.getTrucksID()

    def getTrucksID(self):
        """Get the list of trucks of the company."""

        listResources = self._connector.getList(self.CompanyName, "devices")
        if listResources == None:
            self._bot.sendMessage(
                "Error in the connection with the Resource Catalog")
            return []
        elif len(listResources) == 0:
            self._bot.sendMessage("No devices registered")
            return []
        else:
            trucksList = []
            for truck in listResources:
                if truck["fieldNumber"] == 0:
                    trucksList.append(int(truck["ID"]))

            return trucksList

    def update(self, message):
        """Update the status of the chat.

        Arguments:
        - `message (str)` : the message received from the user.

        Returns:
        - `True` if the procedure is completed.
        - `False` otherwise.
        """

        if self._status == 0:
            if self.trucksIDs == []:
                self._bot.sendMessage("No trucks registered")
                return True
            else:
                inline_keyboard_ = []
                for device in self.trucksIDs:
                    button = InlineKeyboardButton(
                        text=f"Truck {device}", callback_data=f"{device}")
                    inline_keyboard_.append([button])
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=inline_keyboard_)
                self._bot.sendMessage(f"Choose the Truck of company {self.CompanyName}!",
                                      reply_markup=keyboard)
                self._status += 1
                return False

        elif self._status == 1:
            try:
                TruckNumber = int(message)
            except:
                self._bot.sendMessage("Truck ID must be an integer")
                return False
            else:
                if TruckNumber not in self.trucksIDs:
                    self._bot.sendMessage("Choose a valid option")
                    return False
                else:
                    self.getTrace(TruckNumber)
                    return True

    def getTrace(self, TruckNumber: int):
        """Get the trace of a truck."""

        url = self._connector.getOtherServiceURL(self._connector.Localization)
        if url == None:
            self._bot.sendMessage(
                "Error in the connection with the Service Catalog")
            return

        try:
            res = requests.get(f"{url}/{self.CompanyName}/{TruckNumber}/trace")
            res.raise_for_status()
            htmlres = res.text
        except:
            self._bot.sendMessage(
                "Error in the connection with the Localization Service")
        else:
            fileName = f"trace_{TruckNumber}.html"
            with open(fileName, "w") as f:
                f.write(htmlres)
            with open(fileName, "rb") as fout:
                self._bot.sendDocument(fout)
