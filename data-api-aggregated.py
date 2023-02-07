import argparse
import datetime
import json
from time import time

import requests
import dateutil.parser
import dateutil.tz
import textwrap
import sys
import csv

AGGREGATED_SENSORS_QUERY_URL = 'https://data-api.boulderai.com/data/query'

def query_workspace(workspace, startTime, endTime, key):
    url = f'https://data-api.boulderai.com/workspace/{workspace}/sensors?startTime={startTime}&endTime={endTime}'
    headers = {'X-API-Key': f'{key}'}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def query_sensors(data, key):
    headers = {'Content-type': 'application/json', 'X-API-Key': f'{key}'}
    url = AGGREGATED_SENSORS_QUERY_URL
    url += f"?startTime={data['startTime']}&endTime={data['endTime']}"
    print(f'Issuing curl "{url}" -d \'{json.dumps(data)}\' \\\n'
          f'-X POST \\\n'
          f'-H "Content-Type: application/json" \\\n'
          f'-H "X-API-Key: {key}"')
    r = requests.post(url, data=json.dumps(data), headers=headers)
    r.raise_for_status()
    return r.json()

def time_parse(args, parser):
    format_str = "%Y-%m-%dT%H:%M:%S.000Z"
    if args.startTime is not None:
        passed_start_time = args.startTime
        start_date = dateutil.parser.parse(args.startTime)
        args.startTime = start_date.astimezone(dateutil.tz.UTC).strftime(format_str)
        print(f'converted start time {passed_start_time} to UTC time value {args.startTime}')
    if args.endTime is not None:
        passed_end_time = args.endTime
        end_date = dateutil.parser.parse(args.endTime)
        args.endTime = end_date.astimezone(dateutil.tz.UTC).strftime(format_str)
        print(f'converted end time {passed_end_time} to UTC time value {args.endTime}')
    else:
        args.endTime = datetime.datetime.now().astimezone(dateutil.tz.UTC).strftime(format_str)
        end_date = dateutil.parser.parse(args.endTime)
        print(f'endTime not specified, using time now ({args.endTime})')
    if args.lastDays is not None:
        args.startTime = (end_date - datetime.timedelta(days=args.lastDays)).strftime(format_str)
        print(f'lastDays {args.lastDays} specified, used this to set startTime to {args.startTime}')
    if args.lastHours is not None:
        args.startTime = (end_date - datetime.timedelta(hours=args.lastHours)).strftime(format_str)
        print(f'lastHours {args.lastHours} specified, used this to set startTime to {args.startTime}')
    if args.lastMinutes is not None:
        args.startTime = (end_date - datetime.timedelta(minutes=args.lastMinutes)).strftime(format_str)
        print(f'lastMinutes {args.lastMinutes} specified, used this to set startTime to {args.startTime}')

    if args.startTime is None or args.endTime is None:
        print(f'Time range not specified for query')
        parser.print_help()
        raise ValueError('Invalid arguments')

def get_device_sensor_map( workspace, startTime, endTime, key):
    workspace_data = query_workspace(workspace, startTime, endTime, key)
    sensor_map = {}
    for data in workspace_data:
        if data['deviceId'] not in sensor_map:
            sensor_map[data['deviceId']] = set()
        sensor_map[data['deviceId']].add(data['sensorName'])
    return sensor_map

def utc2local(utc_str):
    from_zone = dateutil.tz.tzutc()
    to_zone = dateutil.tz.tzlocal()
    utc = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.000Z')
    utc = utc.replace(tzinfo=from_zone)
    local = utc.astimezone(to_zone)
    return local

def write_to_csv( csvfile, results ):
    result_dict = {}
    sensor_labels = set()
    for result in results:
        if result['windowStart'] not in result_dict:
            result_dict[result['windowStart']] = {}
        sensor_label = result['sensorName'] + " " + result['direction']
        sensor_labels.add(sensor_label)
        result_dict[result['windowStart']][sensor_label] = result['values'][0]['value']
        result_dict[result['windowStart']]['windowEnd'] = result['windowEnd']

    with open(csvfile, 'w') as file:
        writer = csv.writer(file)
        row = [f"Window Start {dateutil.tz.tzlocal().tzname(datetime.datetime.now())}",
                f"Window End {dateutil.tz.tzlocal().tzname(datetime.datetime.now())}"]
        row.extend(list(sensor_labels))
        writer.writerow(row)
        for start_time in result_dict.keys():
            values = []
            for label in sensor_labels:
                values.append(int(result_dict[start_time][label]))
            row = [utc2local(start_time), utc2local(result_dict[start_time]['windowEnd'])]
            row.extend(values)
            writer.writerow(row)
        print(f"Wrote {csvfile}")

def sensor_query():
    parser = argparse.ArgumentParser(description="Data API query tool for the Sigthhound Data API",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent('''\
    Examples:
    Query data for all sensors on all devices in the workspace represented by the ID passed
    as the --workspace argument for the last 3 days and write the output to csv file, one per device:
        python data-api-aggregated.py --workspace xxxxxx --key=${API_KEY} --lastDays=3 --csv
    '''))
    parser.add_argument('--lastMinutes',
                        type=int,
                        help="A number of minutes relative to endTime (or now if endTime is not specified) to query")
    parser.add_argument('--lastHours',
                        type=int,
                        help="A number of hours relative to endTime (or now if endTime is not specified) to query")
    parser.add_argument('--lastDays',
                        type=int,
                        help="A number of days relative to endTime (or now if endTime is not specified) to query")
    parser.add_argument('--startTime',
                        help="The start time, accepted in any format dateutil.parser supports.  Optional and not used"
                             "if --lastHours aor --lastDays is specified")
    parser.add_argument('--endTime',
                        help="The end time, accepted in any format dateutil.parser supports.\n"
                             "see https://dateutil.readthedocs.io/en/stable/examples.html#parse-examples.\n"
                             "If not specified, set to now")
    parser.add_argument('--key',
                        help="The API key for the workspace associated with the device (available from the platform)")
    parser.add_argument('--csv',
                        help='Path to output CSV file with aggregated sensor data, one per device ID.')
    parser.add_argument('--workspaceId',
                        help='The workspace ID for the device')
    parser.add_argument('--interval',
                        help='The interval for aggregations (default 30 minutes)',
                        default='30 minutes')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    time_parse(args, parser)
    device_sensor_map = get_device_sensor_map(args.workspaceId, args.startTime, args.endTime, args.key)
    separator = '","'
    for device in device_sensor_map.keys():
        sensors = device_sensor_map[device]
        print(f"Found device {device} with sensors {sensors}")
        data = {'deviceId': f'{device}',
            'sensors': list(sensors),
            'startTime': f'{args.startTime}',
            'endTime': f'{args.endTime}',
            'interval': f'{args.interval}',
            'functions' : ["COUNT"],
            'fillEmptyWindows' : True,
            'order' : 'ASCENDING'}
        result = query_sensors(data, args.key)
        write_to_csv(f"{device}-sensors.csv", result)


if __name__ == '__main__':
    sensor_query()

