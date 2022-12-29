import json
import time
from threading import Thread
from customExceptions import *

class CatalogManager:
    def __init__(self, heading : dict, key_list : list, filename = "catalog.json", autoDeleteTime = 120):
        """Initialize the catalog manager.
        Keyword arguments:
        ``heading`` is a dictionary with the heading of the catalog,
        ``key_list`` is a list of the keys of the lists to be added in the catalog and
        ``filename`` is the name of the file to save the catalog in.
        """
        self.filename = filename
        self.autoDeleteTime = autoDeleteTime
        self.BiggestID = 0
        self.ID_free_list = []

        # try:
        #     fp = open(self.filename, "r")
        #     self.catalog = json.load(fp)
        #     self.catalog["lastUpdate"] = time.time(), 
        #     fp.close()
        # except FileNotFoundError:
        #     self.catalog = heading
        #     self.catalog["lastUpdate"] = time.time(), 
        #     for key in key_list:
        #         self.catalog[key] = []

        self.catalog = heading
        self.catalog["lastUpdate"] = time.time(), 
        for key in key_list:
            self.catalog[key] = []
        self.autoDeleteItemsThread()


    def save(self):
        """Save the catalog in the file specified in the initialization."""
        
        json.dump(self.catalog, open(self.filename, "w"), indent=4)
        print("Catalog saved!\n")
        return json.dumps({"Status": True}, indent=4)

    def get_all(self, list_key : str):
        """Return a json with all the items in the list specified in ``list_key``."""
        
        return json.dumps(self.catalog[list_key], indent=4)

    def get(self, keyword_list, current_list = None):
        """Return the information of ``keyword_list`` in json format.

        Keyword arguments:
        ``keyword_list`` is a list of the keys to search in (nest),
        ``current_list`` is the list to search in (nest). If None, the catalog is searched.
        """
        if len(keyword_list) > 10:
            raise web_exception(400, "Too many keys")

        if current_list == None:
            current_list = self.catalog

        try:    
            if len(keyword_list) == 1:
                return json.dumps(current_list[keyword_list[0]], indent=4)
            else: 
                for item in current_list[keyword_list[0]]:
                    return self.get(keyword_list[1:], item)
        except KeyError:
            raise web_exception(500, "Invalid key")        

    def search(self, list_key : str, key : str, value):
        """Search for a item in the catalog.
        Return a json with the item if found, otherwise return an empty list.

        Keyword arguments: 
        ``list_key`` is the name of the list to search in, 
        ``key`` is the key to search for and
        ``value``is the value to search for
        """
        try:      
            output = []
            for device in self.catalog[list_key]:
                if isinstance(device[key], list):
                    if value in device[key]:
                        output.append(device)
                else:
                    if str(device[key]) == str(value):
                        output.append(device)
            return json.dumps(output, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def insert(self, list_key : str, new_item : dict):
        """Insert a new device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to insert in and
        ``new_item`` is the item in json format to insert
        """
        try:
            if self.ID_free_list:
                ID = self.ID_free_list.pop()
            else:
                self.BiggestID += 1
                ID = self.BiggestID
            actualtime = time.time() 
            self.catalog["lastUpdate"] = actualtime
            new_item["ID"] = ID
            new_item["lastUpdate"] = actualtime
            self.catalog[list_key].append(new_item)
            out = {"ID": ID}
            return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def update(self, list_key : str, new_item : dict):
        """Update a device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to update in and
        ``new_item`` is the item in json format to update
        """
        try:
            is_present = json.loads(self.search(list_key, "ID", new_item["ID"]))
            if len(is_present) == 0:
                out = {"Status": False}
            else:
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                new_item["lastUpdate"] = actualtime
                for i in range(len(self.catalog[list_key])):
                    if str(self.catalog[list_key][i]["ID"]) == str(new_item["ID"]):
                        self.catalog[list_key][i] = new_item
                        break
                out = {"Status": True}
            return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")

    def delete(self, IDvalue : int):
        """Delete a item from the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``IDvalue`` is the ID of the item to delete
        """
        try:
            current_list = self.find_list(IDvalue)
            if current_list != None:
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                for i in range(len(current_list)):
                    if current_list[i]["ID"] == IDvalue:
                        current_list.pop(i)
                        self.ID_free_list.append(IDvalue)
                        break
                out = {"Status": True}
            else:
                out = {"Status": False}
            return json.dumps(out, indent=4)
        except KeyError:
            raise web_exception(500, "Invalid key")
    
    def find_list(self, IDvalue : int):
        for key in self.catalog:
            if isinstance(self.catalog[key], list):
                for item in self.catalog[key]:
                    if item["ID"] == IDvalue:
                        return self.catalog[key]
        return None

    def find_item(self, IDvalue : int) :
        current_list = self.find_list(IDvalue)
        if current_list != None:
            for item in current_list:
                if item["ID"] == IDvalue:
                    return item
        return None

    def refreshItem(self, IDvalue : int):
        """Refresh the lastUpdate field of a device.
        Return a json with the status of the operation.

        Keyword arguments:
        ``IDvalue`` is the ID of the item to refresh
        """

        item = self.find_item(IDvalue)
        if item != None:
            actualtime = time.time()
            self.catalog["lastUpdate"] = actualtime
            item["lastUpdate"] = actualtime
            out = {"Status": True}
        else:
            out = {"Status": False}
        return json.dumps(out, indent=4)


    def autoDeleteItems(self):
        """Refresh the catalog removing the devices that are not online anymore."""
        while True:
            actualtime = time.time()
            for key in self.catalog:
                if isinstance(self.catalog[key], list):
                    for device in self.catalog[key]:
                        try:
                            if actualtime - device["lastUpdate"] > self.autoDeleteTime:
                                self.ID_free_list.append(device["ID"])
                                self.catalog[key].remove(device)
                        except KeyError:
                            print("Device without lastUpdate field")
                            self.catalog[key].remove(device)
            self.catalog["lastUpdate"] = actualtime
            time.sleep(self.autoDeleteTime)

    def autoDeleteItemsThread(self):
        """Start the thread that refresh the catalog removing the devices that are not online anymore."""
        t = Thread(target=self.autoDeleteItems)
        t.daemon = True
        t.start()    