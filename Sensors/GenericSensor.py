import requests
import json

Help_str = """Available Command:
searchByName:        print all the information about the devices for the given
searchByID:          print all the information about the devices for the given
searchByService:     print all the information about the devices that provides the given
searchByMeasureType: print all the information about the device that provides such measure
insertDevice:        insert a new device it that is not already present on the list (the ID is checked). Otherwise
                     ask the end-user to update the information about the existing device with the new parameters. 
printAll:            print the full catalog
exit:                save the catalog (if changed) in the same JSON file provided as input.
"""

class Client: 
    def __init__(self, url) :
        self.url = url

    def run(self) :
        print("\nType 'help' for the list of available commands")
        while True :
            command = input(">> ").lower()
            if command == "exit" :
                self.exit()
                return False
            elif command == "help" :
                print(Help_str)
                return True
            else:
                try:
                    self.switch(command)
                    return True
                except SyntaxError:
                    pass

    def switch(self, command) :
        if command == "printall":
            out = self.get(self.url + "printall")
            if out:
                self.print_result(out)
        elif command == "searchbyname":
            self.searchby(command, "deviceName")
        elif command == "searchbyid":
            self.searchby(command, "deviceID")
        elif command == "searchbyservice":
            self.searchby(command, "availableServices")
        elif command == "searchbymeasuretype":
            self.searchby(command, "measureType")
        elif command == "insertdevice":
            print(self.insert_device())
        else:
            print("Invalid command\n")
            raise SyntaxError
        
    def searchby(self, command, field):
        value = input(f"Insert the {field} value: ")       
        out = self.get(self.url + command, {field: value})
        if out != None:
            if len(out) > 0:
                self.print_result(out)
            else:
                print("No device found\n")

    def insert_device(self):
        deviceID = input("Insert the deviceID: ")
        
        is_present = self.get(self.url + "ispresent", {"deviceID": deviceID})
        if is_present != None:
            if is_present["Found"] == True:
                print("Device already present in the database")
                if not query_yes_no(f"Do you want to update the device {deviceID}? "):
                    return "Device not updated as requested\n" 
                else:
                    if len(new_device := self.load_device()) > 0:
                        res = self.put(self.url + "updatedevice", new_device)
                        if res != None:
                            if res["Status"] == True:
                                return("Device updated\n")
                    return("Device not updated\n")
            else:
                # If the device is not present, insert it
                if len(new_device := self.load_device()) > 0:
                    res = self.post(self.url + "insertdevice", new_device)
                    if res != None:
                        if res["Status"] == True:
                            return("Device inserted\n")
                return("Device not inserted\n")
        else:  
            return("Error in checking if the device is present\n")

    def load_device(self):
        try:
            file_newdevice = input("Insert the file name of the device (json file): ")
            new_device_dict = json.load(open(file_newdevice, "r")) 
            return json.dumps(new_device_dict, indent=4)
        except:
            print("Error in loading the device\n")
            return ""

    def print_result(self, out_json) :
        print(json.dumps(out_json, indent=4))

    def exit(self) :
        out = self.post(self.url + "save")
        if out != None:
            if out["Status"] == True:
                print("Catalog saved\n")
            else:
                print("Catalog not saved\n")

    def get(self, url_complete, params_dict = None):
        try:           
            r = requests.get(url_complete, params = params_dict)
            r.raise_for_status()
            r_json = r.json()
            return r_json
        except requests.exceptions.HTTPError as err:
            print(f"{err.response.status_code} : {err.response.reason}")
            return None
        except:
            print("Unknown error\n")
            return None

    def put(self, url_complete, body):
        try:          
            r = requests.put(url_complete, data=body)
            r.raise_for_status()
            r_json = r.json()
            return r_json
        except requests.exceptions.HTTPError as err:
            print(f"{err.response.status_code} : {err.response.reason}")
            return None
        except:
            print("Unknown error\n")
            return None

    def post(self, url_complete, body = None):
        try:               
            r = requests.post(url_complete, data = body)
            r.raise_for_status()
            r_json = r.json()
            return r_json
        except requests.exceptions.HTTPError as err:
            print(f"{err.response.status_code} : {err.response.reason}")
            return None
        except:
            print("Unknown error\n")
            return None


def query_yes_no(question):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}

    while True:
        choice = input(question + " [Y/n] ").lower()
        if choice == "":
            return valid["yes"]
        elif choice in valid:
            return valid[choice]
        else:
            print(f"Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

if __name__ == "__main__":
    man = Client("http://localhost:8080/")
    while True:
        run = man.run()
        if not run :
            break   
    
    print("End of the program")