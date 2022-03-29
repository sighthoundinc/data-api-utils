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

from google.cloud import storage
import google.auth
import subprocess

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
    event.update(media)
    return event

def pretty_print(data):
    print(json.dumps(data, indent=2))


credentials, project = None, None
gcp_client = None
bucket = None
def download_video(url, filename, use_service_account):
    global credentials, project, gcp_client, bucket
    if not bucket:
        if use_service_account:
            credentials, project = google.auth.default()
            gcp_client = storage.Client(project, credentials)
        else:
            gcp_client = storage.Client()
        bucket = gcp_client.get_bucket(url.split("/")[2])
    
    print(f"Downloading {url.split('/')[-1]} to {filename}")
    blob = bucket.get_blob("/".join(url.split("/")[3:]))
    blob.download_to_filename(filename)

# in my experience, this only works on Windows
def download_video_shell(url, filename):
    cmd_line = [os.environ["CLOUDSDK_ROOT_DIR"] + '\\bin\\gsutil', 'cp', url, filename]
    print(f"Executing {' '.join(cmd_line)}")
    subprocess.call(cmd_line, shell=True)

def get_closest_result(results, time_of_interest):
    if not results:
        return None 

    closest, timeDifference = None, None
    for result in results:
        difference = date_parser.parse(result['timeCollected']) - time_of_interest
        if not timeDifference:
            timeDifference = difference
            closest = result
            continue

        if difference < timeDifference:
            timeDifference = difference
            closest = result
    return closest

if __name__ == '__main__':
    print('Running find media by sensor example...')
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
    parser.add_argument('--num_events', '-n', dest='num_events', type=int,
                        help='number of events to show/save to CSV.  Defaults to 10.', default=10)
    parser.add_argument('--download', '-d', dest='download', action='store_true',
                        help='Save media files to tmp/<eventId>.mp4 for each event', default=False)
    parser.add_argument('--use_service_account', '-s', dest='use_service_account', action='store_true',
                        help='Use environment default GCP service account to download media files', default=False)
    parser.add_argument('--min_timeOn', '-m', dest='min_timeOn', type=float, default=1.5, 
                        help='Minimum amount of time (seconds) that an object must be present in presence zone.')
    parser.add_argument('--csv', default='',
                        help='csv file to write to.  If not specified, will not write to anything')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    client = DataApiClient(api_key=api_key, api_base=api_base)
    stream_id = args.stream_id
    sensors = args.sensors.split(',')

    # We want to look at the last numDays days of data
    numDays = 7
    start = datetime.utcnow() - timedelta(days=numDays)
    end = datetime.utcnow()

    events = client.query_stream_flat(
        StreamQuery(
            stream_id=stream_id,
            sensors=sensors,
            start_time=start,
            end_time=end
        )
    )

    print(f'Found {len(events)} events in the last {numDays} days.')

    if args.csv:
        data_file = open(args.csv, 'w')
        csv_writer = csv.writer(data_file)
        count = 0

    valid_events = 0
    for event in events:
        # filter out events of 1 sec or less
        if "timeOn" in event["meta"] and event["meta"]["timeOn"] <= args.min_timeOn:
            continue
        valid_events += 1
        time_of_interest = date_parser.parse(event['timeCollected'])
        query_start, query_end = get_media_range(time_of_interest, 0, 1)
        results = client.query_media_data(
            MediaQuery(
                stream_id=stream_id,
                start_time=query_start,
                end_time=query_end
            )
        )

        media_event = get_closest_result(results, time_of_interest)

        if media_event:
            print(f'Found media event for event {event["id"]}.')
            print(f"Event: {event}")
            print(f"Media Event:")
            pretty_print(media_event)

            if args.csv:
                merged = {
                    "sensorId": event['sensorId'],
                    "deviceId": event['deviceId'],
                    "event_id": event['id'],
                    "event_timeCollected": event['timeCollected'],
                    "event_timeOn": event['meta']['timeOn'],
                    # "event_meta": event["meta"],
                    "media_id": media_event['id'],
                    "media_timeCollected": media_event['timeCollected'],
                    "media_durationMs": media_event['durationMs'],
                    "media_url": media_event['url'],
                }
                if "timeOn" in event["meta"]:
                    merged["event_timeOn"] = event["meta"]["timeOn"]
                if count == 0:
                    # Writing headers of CSV file
                    header = merged.keys()
                    csv_writer.writerow(header)
                    count += 1

                # Writing data to CSV file
                csv_writer.writerow(merged.values())
        
            if args.download:
                if not os.path.isdir("tmp"):
                    os.mkdir("tmp")
                if not os.path.exists(f'tmp/{event["id"]}.mp4'):
                    if "CLOUDSDK_ROOT_DIR" in os.environ:
                        download_video_shell(media_event['url'], f'tmp/{event["id"]}.mp4')
                    else:
                        download_video(media_event['url'], f'tmp/{event["id"]}.mp4', args.use_service_account)
            if valid_events == args.num_events:
                break

    if args.csv:
        data_file.close()
