import json
import os
from datetime import datetime, timedelta
from typing import List
from dateutil import parser as date_parser

from dotenv import load_dotenv

from api_types import StreamQuery, InProgressEvents, MediaQuery
from client import DataApiClient
import argparse


def run(stream_id: str, sensors: List[str]):
    start =  datetime.now() - timedelta(days=1)
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

    parser = argparse.ArgumentParser(description='In progress example.')
    parser.add_argument('--stream_id', dest='stream_id',
                        help='stream_id to demonstrate', required=True)

    parser.add_argument('--sensors', dest='sensors', help='sensors to query', required=True)

    args = parser.parse_args()

    client = DataApiClient(api_key=api_key, api_base=api_base)
    stream_id = args.stream_id
    sensors = args.sensors.split(',')

    # We want to look at the last 24 hours of data
    start = datetime.now() - timedelta(days=7)
    end = datetime.now()

    results = client.query_stream_flat(StreamQuery(
        stream_id=stream_id,
        sensors=sensors,
        start_time=start,
        end_time=end
    ))

    print(f'Found {len(results)} events.')
    for result in results[:10]:
        print(result)
