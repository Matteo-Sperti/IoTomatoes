import time

keys_to_ignore = ['CompanyName', 'status', 'OnTime',
                  'control', 'Consumption_kWh', 'lastMeasure', 'lastUpdate']

class CheckResult():
    """Class to return a result of a check."""

    def __init__(self, is_error: bool = False, messageType: str = "", message: str = "",
                 device_id: int = -1, measure_type: str = ""):
        """Constructor of the class.

        Arguments:
        - `is_error (bool)`: True if the check has found an error
        - `messageType (str)`: Type of the message
        - `message (str)`: Message to return
        - `device_id (int)`: ID of the device
        - `measure_type (str)`: Type of the measure
        """
        self.is_error = is_error
        self.message = message
        self.messageType = messageType
        self.device_id = device_id
        self.measure_type = measure_type


def compareLists(connector, new_deviceList: list, msg_on: bool = False):
    """If there are changes in the device list, update the old list and 
    notify the company"""

    for new_dev in new_deviceList:
        old_dev_iter = filter(lambda d: d.get(
            'ID') == new_dev['ID'], connector.deviceList)

        not_present = True
        for d in old_dev_iter:
            not_present = False
            if _different_dicts(d, new_dev, keys_to_ignore):
                for key in keys_to_ignore:
                    new_dev[key] = d[key]
                d.update(new_dev)
                if msg_on:
                    payload = connector._message.copy()
                    payload['cn'] = new_dev['CompanyName']
                    payload['msg'] = f"Device {new_dev['ID']} updated."
                    payload['msgType'] = 'Update'
                    payload['t'] = time.time()
                    connector._MQTTClient.myPublish(
                        f"{new_dev['CompanyName']}/{connector._MQTTClient.publishedTopics[0]}", payload)

        if not_present:
            connector.deviceList.append(new_dev)
            if msg_on:
                payload = connector._message.copy()
                payload['cn'] = new_dev['CompanyName']
                payload['msg'] = f"Device {new_dev['ID']} added."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                connector._MQTTClient.myPublish(
                    f"{new_dev['CompanyName']}/{connector._MQTTClient.publishedTopics[0]}", payload)

    for old_dev in connector.deviceList:
        if old_dev['ID'] not in [d['ID'] for d in new_deviceList]:
            connector.deviceList.remove(old_dev)
            if msg_on:
                payload = connector._message.copy()
                payload['cn'] = old_dev['CompanyName']
                payload['msg'] = f"Device {old_dev['ID']} removed."
                payload['msgType'] = 'Update'
                payload['t'] = time.time()
                connector._MQTTClient.myPublish(
                    f"{old_dev['CompanyName']}/{connector._MQTTClient.publishedTopics[0]}", payload)


def _different_dicts(dict1, dict2, keys_to_ignore):
    """Check if two dictionaries are different"""

    dict1_filtered = {k: v for k,
                      v in dict1.items() if k not in keys_to_ignore}
    dict2_filtered = {k: v for k,
                      v in dict2.items() if k not in keys_to_ignore}

    return dict1_filtered != dict2_filtered
