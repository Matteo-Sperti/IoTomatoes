import time

"""
Functions:\n
	- createDeviceList (list of dict, bool) -> list of dict\n
	- checkUpdate (str, str, str, list of dict, bool) -> None\n
	- inList (list of dict, int) -> bool\n
	- compare_dicts (dict, dict, list of str) -> bool\n
"""
keys_to_ignore = ['CompanyName', 'status', 'OnTime',
                  'control', 'Consumption_kWh', 'lastMeasure', 'lastUpdate']


def createDeviceList(companyList: list):
    """Create a list of all devices integrating informations about 
    the last time a message was received from a device
    Arguments:
    - `companyList (list of dict)`: List of all companies and their devices.
    - `isActuator (bool)`: True if the list should contain only actuators, 
    False if the list should contain only sensors
    Return:
    - `deviceList (list of dict)`: List of all devices updated
    """

    deviceList = []
    for comp in companyList:
        for dev in comp['devicesList']:
            if dev['isActuator']:
                deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                             'status': 'OFF',
                                             'OnTime': 0,
                                             'control': False,
                                             'Consumption_kWh': 0}})
            elif dev['isSensor']:
                deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                             'lastMeasure': None}})
            elif dev['isActuator'] & dev['isSensor']:
                deviceList.append({**dev, **{'CompanyName': comp['CompanyName'],
                                             'lastMeasure': None,
                                             'status': 'OFF',
                                             'OnTime': 0,
                                             'control': False,
                                             'Consumption_kWh': 0}})
    return deviceList


def filterList(deviceList: list, select: str):
    if (select == 'Actuators'):
        deviceList = list(filter(lambda d: d['isActuator'], deviceList))
    elif (select == 'Sensors'):
        deviceList = list(filter(lambda d: d['isSensor'], deviceList))

    return deviceList


def compareLists(Connector, new_deviceList, msg_on: bool = False):
    """Check if there are changes in the ResourceCatalog and update the device list"""

    for new_dev in new_deviceList:
        old_dev_iter = filter(lambda d: d.get(
            'ID') == new_dev['ID'], Connector.deviceList)

        not_present = True
        for d in old_dev_iter:
            not_present = False
            if _different_dicts(d, new_dev, keys_to_ignore):
                for key in keys_to_ignore:
                    new_dev[key] = d[key]
                d.update(new_dev)
                if msg_on:
                    payload = Connector._message.copy()
                    payload['cn'] = new_dev['CompanyName']
                    payload['msg'] = f"Device {new_dev['ID']} updated."
                    payload['msgType'] = 'Update'
                    payload['t'] = time.time()
                    Connector._MQTTClient.myPublish(
                        f"{new_dev['CompanyName']}/{Connector._MQTTClient.publishedTopics[0]}", payload)

        if not_present:
            Connector.deviceList.append(new_dev)
            if msg_on:
                payload = Connector._message.copy()
                payload['cn'] = new_dev['CompanyName']
                payload['msg'] = f"Device {new_dev['ID']} added."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                Connector._MQTTClient.myPublish(
                    f"{new_dev['CompanyName']}/{Connector._MQTTClient.publishedTopics[0]}", payload)

    for old_dev in Connector.deviceList:
        if old_dev['ID'] not in [d['ID'] for d in new_deviceList]:
            Connector.deviceList.remove(old_dev)
            if msg_on:
                payload = Connector._message.copy()
                payload['cn'] = old_dev['CompanyName']
                payload['msg'] = f"Device {old_dev['ID']} removed."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                Connector._MQTTClient.myPublish(
                    f"{old_dev['CompanyName']}/{Connector._MQTTClient.publishedTopics[0]}", payload)


def inList(deviceID: int, deviceList: list):
    """Check if an actuator is in the list of the actuators
    Arguments:
    - `deviceID (int)`: ID of the device to check
    - `deviceList (list of dict)`: List of all devices
    Return: `CheckResult` object with:
    - `error (bool)`: ".is_error"
    - `message (str)`: ".message"
    - `topic (str)`: ".topic" 
    """

    for dev in deviceList:
        if dev['ID'] == deviceID:
            return CheckResult(is_error=False)
    return CheckResult(is_error=True, messageType="Error", message="Device not found")


def _different_dicts(dict1, dict2, keys_to_ignore):

    dict1_filtered = {k: v for k,
                      v in dict1.items() if k not in keys_to_ignore}
    dict2_filtered = {k: v for k,
                      v in dict2.items() if k not in keys_to_ignore}

    return dict1_filtered != dict2_filtered


class CheckResult():
    def __init__(self, is_error: bool = False, messageType: str = "", message: str = "",
                 device_id: int = -1, measure_type: str = ""):
        self.is_error = is_error
        self.message = message
        self.messageType = messageType
        self.device_id = device_id
        self.measure_type = measure_type
