import argparse
from dotenv import load_dotenv
import os
import sys
import json

from client import DataApiClient
from api_types import LatestStatusByWorkspaceQuery, SensorsByDeviceQuery
from utils import *

LOW_STORAGE_THRESHOLD = 90      # % storage used to mark low storage
LAST_SEEN_THRESHOLD = 60*20     # number of seconds since last ping to consider a device offline
CHECK_FOR_DATA_HOURS = 24       # how far back to check for device data


def parse_args():
    parser = argparse.ArgumentParser(
        description='Device status check example.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-w', '--workspace_id',
                        help='Workspace ID of the workspace to run the device status check on.',
                        type=str, required=True)
    parser.add_argument('-d', '--device_list',
                        help='A JSON file which contains a list of deviceIds of interest.',
                        type=str)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args()


def service_status(service_name: str, devices: dict):
    running = 0
    not_running = {}
    for device, status in devices.items():
        if status == 'RUNNING':
            running += 1
        else:
            if status not in not_running:
                not_running[status] = []
            not_running[status].append(device)

    print(f"=> {service_name}")
    print(f"\t- Running on {running} device(s)")
    if not_running:
        print(f"\t- Not running on {len(devices)-running} device(s):")
        for status in not_running:
            print(f"\t\t- In {status} state on {', '.join(not_running[status])}")


if __name__ == '__main__':
    print(f"Running device status check...")
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    api_base = os.environ.get("API_BASE")

    if not api_key:
        print('Please set the API_KEY environment variable.')
        print('e.g. `export API_KEY="38ed7729792c48489945c8060255fa45"`')
        exit(1)
    if not api_base:
        api_base = 'https://data-api.boulderai.com/'

    args = parse_args()
    client = DataApiClient(api_key=api_key, api_base=api_base)
    data = client.query_status_by_workspace(
        LatestStatusByWorkspaceQuery(
            workspace_id=args.workspace_id
        )
    )["data"]
    # print(f"Data => {json.dumps(data, indent=2)}")

    devices = None
    if args.device_list:
        with open(args.device_list, 'r') as f:
            devices = json.load(f)
    services = {}
    low_storage = {}
    not_low_storage = []
    online = []
    offline = {}
    for device in data:
        device_id = device['deviceId']
        # check services
        if devices and device_id not in devices:
            continue
        for service in device['services']:
            if service['name'] not in services:
                services[service['name']] = {}
            services[service['name']][device_id] = service['status']['status']
        # check low storage
        if device['dataMemoryStorage']['percentageUse'] > LOW_STORAGE_THRESHOLD:
            low_storage[device_id] = device['dataMemoryStorage']['percentageUse']
        else:
            not_low_storage.append(device_id)
        # check last seen
        last_seen = datetime.datetime.strptime(device['lastSeen'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        time_since_last_seen = datetime.datetime.utcnow() - last_seen
        if time_since_last_seen.seconds > LAST_SEEN_THRESHOLD:
            offline[device_id] = time_since_last_seen.seconds
        else:
            online.append(device_id)


    has_sensor_data = []
    no_sensor_data = []
    for device_id in devices:
        query_start, query_end = get_media_range(datetime.datetime.utcnow(), CHECK_FOR_DATA_HOURS*60, 0)
        sensors = client.query_sensors_by_device(
            SensorsByDeviceQuery(
                device_id=device_id,
                start_time=query_start,
                end_time=query_end
            )
        )
        [has_sensor_data.append(device_id) if sensors else no_sensor_data.append(device_id)]

    print(f"\nServices Status Check:")
    for name, device in services.items():
        service_status(name, device)

    print(f"\nRecent Data Check:")
    print(f"=> {len(has_sensor_data)} device(s) have sensor data in the last {CHECK_FOR_DATA_HOURS} hours.")
    if no_sensor_data:
        print(f"=> The following device(s) have no sensor data in the last {CHECK_FOR_DATA_HOURS} hours: {no_sensor_data}")

    print(f"\nLow Storage Check:")
    if low_storage:
        print(f"=> {len(low_storage)} device(s) are low on storage:")
        for device, percentage_used in low_storage.items():
            print(f"\t- {device} storage is {percentage_used}% full")
    else:
        print(f"=> All {len(not_low_storage)} devices are not low on storage.")

    print(f"\nDevice Connectivity Check:")
    print(f"=> {len(online)} device(s) are online.")
    if offline:
        print(f"=> {len(offline)} device(s) appear offline:")
        for device, time_since in offline.items():
            print(f"\t- {device} was last seen ~{int(time_since/60)} minutes ago")

