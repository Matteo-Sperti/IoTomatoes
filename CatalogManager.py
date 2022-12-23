import json
import cherrypy
import time

refreshTime = 30

class InvalidRequest(Exception):
    def __init__(self, message):
        self.message = message

class CatalogManager:
    def __init__(self, heading : dict, key_list : list, filename = "catalog.json"):
        """Initialize the catalog manager.
        Keyword arguments:
        ``heading`` is a dictionary with the heading of the catalog,
        ``key_list`` is a list of the keys of the lists to be added in the catalog and
        ``filename`` is the name of the file to save the catalog in.
        """
        self.filename = filename

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

    def print(self, list_key : str):
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

    def refresh(self):
        """Refresh the catalog removing the devices that are not online anymore."""

        actualtime = time.time()
        for key in self.catalog:
            if isinstance(self.catalog[key], list):
                for device in self.catalog[key]:
                    try:
                        if actualtime - device["lastUpdate"] > refreshTime:
                            self.catalog[key].remove(device)
                    except KeyError:
                        print("Device without lastUpdate field")
                        self.catalog[key].remove(device)
        self.catalog["lastUpdate"] = actualtime
        time.sleep(refreshTime)

class WebPage(object):
    exposed = True

    def GET(self, *uri, **params):
        try:
            if len(uri) == 0:
                raise InvalidRequest("No command received")
            elif uri[0] == "print" and len(uri) == 2:
                return Catalog.print(uri[1])
            elif uri[0] == "search" and len(uri) == 3:
                return Catalog.search(uri[1], uri[2], params[uri[2]])
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
            if len(uri) == 2 and uri[0] == "update":
                body_dict = json.loads(cherrypy.request.body.read())
                return Catalog.update(uri[1], body_dict)
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
            if len(uri) == 1 and uri[0] == "save":
                return Catalog.save()
            if len(uri) == 2 and uri[0] == "insert":
                body_dict = json.loads(cherrypy.request.body.read())
                return Catalog.insert(uri[1], body_dict)
            else:
                raise InvalidRequest("Invalid command")
        except InvalidRequest as e:
            print(e.message)
            raise cherrypy.HTTPError(400, e.message)
        except:
            e_string = "Unknown server error"
            print(e_string)
            raise cherrypy.HTTPError(500, e_string)

if __name__ == "__main__":
    settings = json.load(open("settings.json"))

    ip_address = settings["REST_settings"]["ip_address"]
    port = settings["REST_settings"]["port"]

    heading = {
        "projectOwner": settings["owner"], 
        "projectName": settings["projectName"],
        "broker": settings["broker"],
        }
    key_list = ["farmsList", "devicesList", "usersList"]

    Catalog = CatalogManager(heading, key_list, settings["filename"])

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    webService = WebPage()
    cherrypy.tree.mount(webService, '/', conf)
    cherrypy.config.update({'server.socket_host': ip_address})
    cherrypy.config.update({'server.socket_port': port})
    cherrypy.engine.start()

    while True:
        try:
            Catalog.refresh()
        except KeyboardInterrupt:
            break
    cherrypy.engine.block()
    Catalog.save()
    print("Server stopped")