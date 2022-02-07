import json
import csv
import os, sys, textwrap
from datetime import datetime, timedelta
from typing import List
from dateutil import parser as date_parser

from dotenv import load_dotenv

from api_types import StreamQuery, InProgressEvents, MediaQuery
from client import DataApiClient
import argparse

from utils import get_media_range


def run(stream_id: str, sensors: List[str]):
    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    query = StreamQuery(stream_id=stream_id, sensors=sensors, start_time=start, end_time=end)
    response = client.query_stream_flat(query)

    print(json.dumps(response[:3], indent=2))
    length = len(response)
    print(f'Response length => {length}')


def objects_in_region(input: json):
    try:
        return int(input['meta']['numObjectsInRegion'])
    except KeyError:
        return 0


def get_object_id(event: json):
    return event['meta']['object']['uniqueId']


def get_event_by_object_id(events, object_id):
    events_with_object = []
    for event in events:
        if (get_object_id(event) == object_id):
            events_with_object.append(event)
    return events_with_object


# Python code to merge dict using update() method
def merge(event, media):
    return (event.update(media))


if __name__ == '__main__':
    print('Running in object correlation example...')
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    api_base = os.environ.get("API_BASE")

    if not api_key:
        print('Please set the API_KEY environment variable.')
        print('e.g. `export API_KEY="38ed7729792c48489945c8060255fa45"`')
        exit(1)

    if not api_base:
        api_base = 'https://data-api.boulderai.com/'

    parser = argparse.ArgumentParser(description='Find media by sensor example.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent('''\
    Example:
        export API_KEY="38ed7729792c48489945c8060255fa45"
        python3 src/find_media_by_sensor.py --stream_id BAI_0000134 --sensors 0__PRESENCE_PERSON_1
    '''))
    parser.add_argument('--stream_id', dest='stream_id',
                        help='stream_id to demonstrate. If using a DNNCam, use the device ID (i.e. BAI_0000134). '
                             'Else, query for sensors on a device to get associated streamIds, '
                             'see https://docs.data-api.sighthound.com/#get-sensors-by-device', required=True)
    parser.add_argument('--sensors', dest='sensors',
                        help='sensors to fetch data from.  These should be formatted as <streamUUID>__<sensorName> '
                             'where the streamUUID should be 0 for DNNCams. For example, if you would like to view the '
                             'events from the PRESENCE_PERSON_1 sensor on a DNNCam, the sensor name would be 0__PRESENCE_PERSON_1.', required=True)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    client = DataApiClient(api_key=api_key, api_base=api_base)
    stream_id = args.stream_id
    sensors = args.sensors.split(',')

    # We want to look at the last 24 hours of data
    start = datetime.now() - timedelta(days=7)
    end = datetime.now()

    events = client.query_stream_flat(
        StreamQuery(
            stream_id=stream_id,
            sensors=sensors,
            start_time=start,
            end_time=end
        )
    )

    print(f'Found {len(events)} events.')

    # now we will open a file for writing
    data_file = open('data_file.csv', 'w')

    # create the csv writer object
    csv_writer = csv.writer(data_file)

    # Counter variable used for writing
    # headers to the CSV file
    count = 0

    for event in events[:10]:
        time_of_interest = date_parser.parse(event['timeCollected'])
        query_start, query_end = get_media_range(time_of_interest, 0, 1)
        results = client.query_media_data(
            MediaQuery(
                stream_id=stream_id,
                start_time=query_start,
                end_time=query_end
            )
        )

        # if len(results) == 1:
        #     merged = merge(event, results[0])
        #     if count == 0:
        #         # Writing headers of CSV file
        #         header = merged.keys()
        #         csv_writer.writerow(header)
        #         count += 1

        #     # Writing data to CSV file
        #     csv_writer.writerow(merged.values())

        print(f'Found {len(results)} events.')
        for result in results[:10]:
            print(event)
            print(result)
