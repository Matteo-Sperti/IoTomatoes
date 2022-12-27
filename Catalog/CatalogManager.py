import json
import time
import threading
import cherrypy
from CustomExceptions import InvalidRequest

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

        try:
            fp = open(self.filename, "r")
            self.catalog = json.load(fp)
            self.catalog["lastUpdate"] = time.time(), 
            fp.close()
        except FileNotFoundError:
            self.catalog = heading
            self.catalog["lastUpdate"] = time.time(), 
            for key in key_list:
                self.catalog[key] = []
        finally:
            t = threading.Thread(target=self.autoDeleteItems)
            t.daemon = True
            t.start()

    def get_singleList(self, list_key : str):
        """Return the list ``list_key`` in json format."""

        try:
            return json.dumps(self.catalog[list_key], indent=4)
        except KeyError: 
            raise InvalidRequest("Invalid list name")

    def save(self):
        """Save the catalog in the file specified in the initialization."""
        json.dump(self.catalog, open(self.filename, "w"), indent=4)
        print("Catalog saved!\n")
        return json.dumps({"Status": True}, indent=4)

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
            raise InvalidRequest("Invalid key")

    def insert(self, list_key : str, new_item : dict):
        """Insert a new device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to insert in and
        ``new_item`` is the item in json format to insert
        """
        try:
            ID_key = list_key.replace("sList","ID")
            is_present = json.loads(self.search(list_key, ID_key, new_item[ID_key]))
            if len(is_present) > 0:
                out = {"Status": False}
            else:
                actualtime = time.time() 
                self.catalog["lastUpdate"] = actualtime
                new_item["lastUpdate"] = actualtime
                self.catalog[list_key].append(new_item)
                out = {"Status": True}
            return json.dumps(out, indent=4)
        except KeyError:
            raise InvalidRequest("Invalid key")

    def update(self, list_key : str, new_item : dict):
        """Update a device in the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to update in and
        ``new_item`` is the item in json format to update
        """
        try:
            ID_key = list_key.replace("sList","ID")
            is_present = json.loads(self.search(list_key, ID_key, new_item[ID_key]))
            if len(is_present) == 0:
                out = {"Status": False}
            else:
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                new_item["lastUpdate"] = actualtime
                for i in range(len(self.catalog[list_key])):
                    if str(self.catalog[list_key][i][ID_key]) == str(new_item[ID_key]):
                        self.catalog[list_key][i] = new_item
                        break
                out = {"Status": True}
            return json.dumps(out, indent=4)
        except KeyError:
            raise InvalidRequest("Invalid key")

    def delete(self, list_key : str, IDvalue):
        """Delete a device from the catalog.
        Return a json with the status of the operation.
        
        Keyword arguments:
        ``list_key`` is the name of the list to delete from and
        ``ID`` is the ID of the item to delete
        """
        try:
            ID_key = list_key.replace("sList","ID")
            is_present = json.loads(self.search(list_key, ID_key, IDvalue))
            if len(is_present) == 0:
                out = {"Status": False}
            else:
                actualtime = time.time()
                self.catalog["lastUpdate"] = actualtime
                for i in range(len(self.catalog[list_key])):
                    if str(self.catalog[list_key][i][ID_key]) == str(IDvalue):
                        self.catalog[list_key].pop(i)
                        break
                out = {"Status": True}
            return json.dumps(out, indent=4)
        except KeyError:
            raise InvalidRequest("Invalid key")

    def autoDeleteItems(self):
        """Refresh the catalog removing the devices that are not online anymore."""

        actualtime = time.time()
        for key in self.catalog:
            if isinstance(self.catalog[key], list):
                for device in self.catalog[key]:
                    try:
                        if actualtime - device["lastUpdate"] > self.autoDeleteTime:
                            self.catalog[key].remove(device)
                    except KeyError:
                        print("Device without lastUpdate field")
                        self.catalog[key].remove(device)
        self.catalog["lastUpdate"] = actualtime
        time.sleep(self.autoDeleteTime)
    
class RESTServiceCatalog(CatalogManager):
    exposed = True

    def __init__(self, heading : dict, filename = "ServiceCatalog.json", autoDeleteTime = 120):
        self.list_name = "servicesList"
        self.base_uri = "ServiceCatalog"
        super().__init__(heading, [self.list_name], filename, autoDeleteTime)

    def GET(self, *uri, **params):
        try:
            if len(uri) < 2:
                raise InvalidRequest("No command received")
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "getAll":
                return self.get_singleList(self.list_name)
            elif len(uri) == 3 and uri[0] == self.base_uri and uri[1] == "search":
                return self.search(self.list_name, uri[2], params[uri[2]])
            else:
                raise InvalidRequest("Invalid command")
                    
        except InvalidRequest as e:
            print(e.message)
            raise cherrypy.HTTPError(400, e.message)
        except KeyError:
            e_string = "Invalid key"
            print(e_string)
            raise cherrypy.HTTPError(400, e_string)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)
        
    def PUT(self, *uri, **params):
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "update":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.update(self.list_name, body_dict)
            else:
                raise InvalidRequest("Invalid command")
        except InvalidRequest as e:
            print(e.message)
            raise cherrypy.HTTPError(400, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

    def POST(self, *uri, **params):
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "save":
                return self.save()
            elif len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "insert":
                body_dict = json.loads(cherrypy.request.body.read())
                return self.insert(self.list_name, body_dict)
            else:
                raise InvalidRequest("Invalid command")
        except InvalidRequest as e:
            print(e.message)
            raise cherrypy.HTTPError(400, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

    def DELETE(self, *uri, **params):
        try:
            if len(uri) == 2 and uri[0] == self.base_uri and uri[1] == "delete":
                return self.delete(self.list_name, params["ID"])
            else:
                raise InvalidRequest("Invalid command")
        except InvalidRequest as e:
            print(e.message)
            raise cherrypy.HTTPError(400, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

class ResourceCatalog(CatalogManager):
    def __init__(self, filename = "ResourceCatalog.json", autoDeleteTime = 120):
        heading = {"lastUpdate": 0, "resourcesList": []}
        key_list = ["CompanyList"]
        super().__init__(heading, key_list, filename, autoDeleteTime)