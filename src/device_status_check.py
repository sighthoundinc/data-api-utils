import argparse
from dotenv import load_dotenv
import os
import sys
import json

from client import DataApiClient
from api_types import LatestStatusByWorkspaceQuery


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
    print('Running device status check...')
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
    for device in data:
        device_id = device['deviceId']
        if devices and device_id not in devices:
            continue
        for service in device['services']:
            if service['name'] not in services:
                services[service['name']] = {}
            services[service['name']][device_id] = service['status']['status']
        if device['mainMemoryStorage']['percentageUse'] > 95:
            low_storage[device_id] = device['mainMemoryStorage']['percentageUse']

    print(f"\nStopped Services Status:")
    for name, devices in services.items():
        service_status(name, devices)

    if low_storage:
        print(f"\nLow Storage Status:")
        for device, percentage_used in low_storage.items():
            print(f"\t- {device} storage is {percentage_used}% full")

