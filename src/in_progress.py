import json
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv

from api_types import StreamQuery, InProgressEvents
from client import DataApiClient
import argparse


def run(api_client: DataApiClient, stream_id: str, sensors: List[str], in_progress_events: InProgressEvents):
    start = datetime(2021, 11, 23, 0)
    end = datetime(2021, 11, 24, 0)
    query = StreamQuery(stream_id=stream_id, sensors=sensors, start_time=start, end_time=end,
                        in_progress_events=in_progress_events)
    response = client.query_stream_flat(query)

    print(json.dumps(response[:3], indent=2))
    length = len(response)
    print(f'Response length => {length}')


if __name__ == '__main__':
    print('Running in progress example...')
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
    sensors = args.sensors
    run(api_client=client, stream_id=stream_id, sensors=sensors, in_progress_events=InProgressEvents.ONLY)

    run(api_client=client, stream_id=stream_id, sensors=sensors, in_progress_events=InProgressEvents.NONE)

    run(api_client=client, stream_id=stream_id, sensors=sensors, in_progress_events=InProgressEvents.INCLUDE)
