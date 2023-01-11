import requests
import sys
sys.path.append('../')
from SupportClasses.CheckResult import *

"""Functions:\n
	- createDeviceList (list of dict, bool) -> list of dict\n
	- checkUpdate (str, str, str, list of dict, bool) -> None\n
	- inList (list of dict, int) -> bool\n
	- compare_dicts (dict, dict, list of str) -> bool\n
	"""
def createDeviceList(companyList : list, isActuator: bool = False):
	"""Create a list of all devices integrating informations about the last time a message was received from a device\n
	Parameters:\n
			- companyList (list of dict) - 'List of all companies and their devices'\n
			- isActuator (bool) - 'True if the list should contain only actuators, False if the list should contain only sensors'\n
	return: \n
		- deviceList (list of dict) - 'List of all devices updated'"""
	deviceList = []
	for comp in companyList:
		for dev in comp['devicesList']:
			if dev['isActuator']&isActuator:
				deviceList.append({**dev, **{'Datetime' : None, 'status': 'OFF', 'OnTime': 0, 'control': False}})
			elif dev['isSensor']&(isActuator == False):
				deviceList.append({**dev, **{'lastUpdate' : None}})
	return deviceList

def getDevicesList(ResourceCatalog_url : str, SystemToken: str, isActuator : bool) :
	try:
		r = requests.get(f'{ResourceCatalog_url}/all', params={"SystemToken": SystemToken})
		r.raise_for_status()
	except requests.exceptions.HTTPError as err:
		print(f"{err.response.status_code} - {err.response.reason}")
		return []
	except:
		print("Error, Resource Catalog not reachable")
		return []
	else:
		CompanyList = r.json()   
		print(CompanyList)      
		deviceList = createDeviceList(CompanyList, isActuator)

		return deviceList

def checkUpdate(Connector, isActuator: bool):
	"""Check if there are changes in the ResourceCatalog and update the device list"""
	new_deviceList = getDevicesList(Connector.ResourceCatalog_url, Connector._SystemToken, isActuator)
	for new_dev in new_deviceList:

		old_dev_iter = filter(lambda d: d.get('ID') == new_dev['ID'], Connector.deviceList)

		not_present = True
		for d in old_dev_iter:
			not_present = False
			if _compare_dicts(d, new_dev, keys_to_ignore=['Datetime', 'lastUpdate', 'status', 'OnTime', 'control']):
				d.update(new_dev)
				payload = {'message': f"Device {new_dev['ID']} updated."}
				Connector.myPublish(f"{Connector.baseTopic}/{new_dev['companyName']}/{Connector._publishedTopics[3]}", payload)

		if not_present:
			Connector.deviceList.append(new_dev)
			payload = {'message': f"Device {new_dev['ID']} added."}
			Connector.myPublish(f"{Connector.baseTopic}/{new_dev['companyName']}/{Connector._publishedTopics[3]}", payload)

	for old_dev in Connector.deviceList:
		if old_dev['ID'] not in [d['ID'] for d in new_deviceList]:
			Connector.deviceList.remove(old_dev)
			payload = {'message': f"Device {old_dev['ID']} removed."}
			Connector.myPublish(f"{Connector.baseTopic}/{old_dev['companyName']}/{Connector._publishedTopics[3]}", payload)


def inList(deviceID : int, deviceList : list):
	"""Check if an actuator is in the list of the actuators\n
	Parameters:\n
		- deviceID (int) - 'ID of the device to check'\n
		- deviceList (list of dict) - 'List of all devices'\n
	return: CheckResult object with:\n
		- error (bool): ".is_error"\n
		- message (str): ".message"\n
		-  topic (str): ".topic" """

	for dev in deviceList:
		if dev['ID'] == deviceID:
			return CheckResult(is_error = False)
	return CheckResult(is_error=False, message="Error, Actuator not found", topic="ErrorReported")

def _compare_dicts(dict1, dict2, keys_to_ignore=[]):
	dict1_filtered = {k: v for k, v in dict1.items() if k not in keys_to_ignore}
	dict2_filtered = {k: v for k, v in dict2.items() if k not in keys_to_ignore}
	
	return dict1_filtered == dict2_filtered