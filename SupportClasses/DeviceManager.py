import time
from MyExceptions import CheckResult

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
			if dev['isActuator'] and isActuator:
				deviceList.append({**dev, **{'CompanyName': comp['CompanyName'], 
											'Datetime' : None, 
											'status': 'OFF', 
											'OnTime': 0, 
											'control': False}})
			elif dev['isSensor'] and not isActuator:
				deviceList.append({**dev, **{'lastUpdate' : None, 
											'CompanyName': comp['CompanyName']}})
	return deviceList

def checkUpdate(Connector, isActuator: bool):
	"""Check if there are changes in the ResourceCatalog and update the device list"""
	new_companyList = Connector.getCompaniesList()
	new_deviceList = createDeviceList(new_companyList, isActuator=isActuator)
	for new_dev in new_deviceList:

		old_dev_iter = filter(lambda d: d.get('ID') == new_dev['ID'], Connector.deviceList)

		not_present = True
		for d in old_dev_iter:
			not_present = False
			if _compare_dicts(d, new_dev, keys_to_ignore=['Datetime', 'lastUpdate', 'status', 'OnTime', 'control']):
				d.update(new_dev)
				payload = {'bn' : Connector._EndpointInfo["serviceName"],
							'CompanyName': new_dev['CompanyName'],
							'message': f"Device {new_dev['ID']} updated.",
							'timestamp' : time.time()}
				Connector.myPublish(f"{new_dev['CompanyName']}/{Connector._publishedTopics[3]}", payload)

		if not_present:
			Connector.deviceList.append(new_dev)
			payload = {'bn' : Connector._EndpointInfo["serviceName"],
						'CompanyName': new_dev['CompanyName'],
						'message': f"Device {new_dev['ID']} added.",
						'timestamp' : time.time()}
			Connector.myPublish(f"{new_dev['CompanyName']}/{Connector._publishedTopics[3]}", payload)

	for old_dev in Connector.deviceList:
		if old_dev['ID'] not in [d['ID'] for d in new_deviceList]:
			Connector.deviceList.remove(old_dev)
			payload = {'bn' : Connector._EndpointInfo["serviceName"],
						'CompanyName': old_dev['CompanyName'],
						'message': f"Device {old_dev['ID']} removed.",
						'timestamp' : time.time()}
			Connector.myPublish(f"{old_dev['CompanyName']}/{Connector._publishedTopics[3]}", payload)

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