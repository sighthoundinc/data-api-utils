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
    start = datetime(2021, 11, 27)
    end = datetime(2021, 11, 28)
    query = StreamQuery(stream_id=stream_id, sensors=sensors, start_time=start, end_time=end)
    response = client.query_stream_flat(query)

    print(json.dumps(response[:3], indent=2))
    length = len(response)
    print(f'Response length => {length}')


def objects_in_region(input: json):
    return input['meta']['numObjectsInRegion']


if __name__ == '__main__':
    print('Running in object correlation example...')
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    api_base = os.environ.get("API_BASE")

    parser = argparse.ArgumentParser(description='In progress example.')
    parser.add_argument('--stream_id', dest='stream_id',
                        help='stream_id to demonstrate', required=True)

    parser.add_argument('--sensors', dest='sensors', nargs='+',
                        help='sensors to query', required=True)

    args = parser.parse_args()

    client = DataApiClient(api_key=api_key, api_base=api_base)
    stream_id = args.stream_id
    sensors = [
        '0__PRESENCE_PERSON_1',
        '0__PRESENCE_PERSON_2',
        '0__PRESENCE_PERSON_3',
        '0__PRESENCE_PERSON_4',
        '0__PRESENCE_PERSON_5'
    ]

    start = datetime.now() - timedelta(days=7)
    end = datetime.now()
    global_max_value = None
    for sensor in sensors:
        json = client.query_stream_flat(
            StreamQuery(stream_id=stream_id, sensors=[sensor], start_time=start, end_time=end,
                        in_progress_events=InProgressEvents.ONLY))
        print(f'Length => {len(json)}')
        local_max_value = json[0]
        for stream_data in json:
            if objects_in_region(local_max_value) < objects_in_region(stream_data):
                local_max_value = stream_data

        print(f'Local Max Value => {objects_in_region(local_max_value)} @ {local_max_value["timeCollected"]}')

        if global_max_value is None:
            global_max_value = local_max_value
        else:
            if objects_in_region(local_max_value) > objects_in_region(global_max_value):
                global_max_value = local_max_value

    print(f'Global max objects in region {global_max_value}')

    time_of_interest = date_parser.parse(global_max_value['timeCollected'])
    media_query = MediaQuery(stream_id=global_max_value['streamId'],
                             start_time=time_of_interest - timedelta(hours=6),
                             end_time=time_of_interest)
    media_response = client.query_media_data(media_query)
    for json in media_response:
        print(json)
