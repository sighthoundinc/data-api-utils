import json
import os
from datetime import datetime
from client import DataApiClient
from api_types import StreamQuery, InProgressEvents
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("API_KEY")
api_base = os.environ.get("API_BASE")

client = DataApiClient(api_key=api_key, api_base=api_base)
start = datetime(2021, 11, 23, 0)
end = datetime(2021, 11, 24, 0)
query = StreamQuery(stream_id="BAI_0000729", sensors=['PRESENCE_PERSON_1'], start_time=start, end_time=end,
                    in_progress_events=InProgressEvents.ONLY)
response = client.query_stream_flat(query)

print(json.dumps(response, indent=2))
