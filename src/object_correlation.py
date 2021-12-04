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

    parser = argparse.ArgumentParser(description='In progress example.')
    parser.add_argument('--stream_id', dest='stream_id',
                        help='stream_id to demonstrate', required=True)

    parser.add_argument('--sensors', dest='sensors', help='sensors to query', required=True)

    args = parser.parse_args()

    client = DataApiClient(api_key=api_key, api_base=api_base)
    stream_id = args.stream_id
    sensors = args.sensors.split(',')

    # We want to look at the last 24 hours of data
    start = datetime.now() - timedelta(hours=24)
    end = datetime.now()
    all_events = []
    # For each of the sensors in the provided input
    for sensor in sensors:
        # Query the last 24 hours
        json = client.query_stream_flat(
            StreamQuery(stream_id=stream_id, sensors=[sensor], start_time=start, end_time=end,
                        in_progress_events=InProgressEvents.ONLY))
        print(f'Length => {len(json)}')
        for stream_data in json:
            # We append each event to the overall list of events
            all_events.append(stream_data)

    # Sort the events by the number of objects in region
    sort_events = sorted(all_events, key=objects_in_region, reverse=True)

    print('Top 5 events by number of objects')
    for event in sort_events[:5]:
        time_of_interest = date_parser.parse(event['timeCollected'])
        # Construct a query that looks 15 minutes back and 5 minutes forward
        media_query = MediaQuery(stream_id=event['streamId'],
                                 start_time=time_of_interest - timedelta(minutes=15),
                                 end_time=time_of_interest + timedelta(minutes=5))

        media_response = client.query_media_data(media_query)
        for video_event in media_response:
            video_end = date_parser.parse(video_event['timeCollected'])
            video_start = video_end - timedelta(milliseconds=video_event['durationMs'])
            # Check to see if the time of interest is in the video
            if video_start < time_of_interest < video_end:
                print(f'VIDEO FOUND @ {video_event["url"]}')
                print(f'EVENT => {event}')
                print(f'OFFSET => {time_of_interest - video_start}')
                object_id = get_object_id(event)
                print(f'OBJECT_ID => {object_id}')
                events_with_object = sorted(get_event_by_object_id(all_events, object_id),
                                            key=lambda e: e['timeCollected'])
                print(f'Object Id\tTime Collected\tSensor Id\tObjects in Region\tVideo Offset')
                for ewo in events_with_object:
                    print(
                        f'{object_id}\t{ewo["timeCollected"]}\t{ewo["sensorId"]}\t{objects_in_region(ewo)}\t{date_parser.parse(ewo["timeCollected"]) - video_start}'
                    )
