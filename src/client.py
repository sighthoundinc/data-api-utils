from api_types import StreamQuery, MediaQuery, SensorsByWorkspaceQuery, StreamQueryAggregate
import requests


class DataApiClient:
    """Data API Client"""
    api_base: str
    api_key: str
    headers: dict[str, str]

    def set_headers(self):
        self.headers = {'Content-type': 'application/json', 'X-API-Key': f'{self.api_key}'}

    # Define Stream Endpoints

    def query_stream_aggregate(self, query: StreamQueryAggregate):
        """http://docs.data-api.boulderai.com/#query-aggregated-stream-data"""
        print(f'Query => {query.toJSON()}')
        r = requests.post(f'{self.api_base}data/stream/aggregate/query', data=query.toJSON(), headers=self.headers)
        r.raise_for_status()
        return r.json()

    def query_stream_flat(self, query: StreamQuery):
        """http://docs.data-api.boulderai.com/#query-flattened-stream-data"""
        print(f'Query => {query.toJSON()}')
        r = requests.post(f'{self.api_base}data/stream/query', data=query.toJSON(), headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_sensors_by_workspace(self, query: SensorsByWorkspaceQuery):
        """http://docs.data-api.boulderai.com/#get-sensors-by-workspace"""
        r = requests.get(
            f'{self.api_base}workspace/{query.workspace_id}/stream/sensor?startTime={query.start_time}&endTime={query.end_time}',
            headers=self.headers)
        r.raise_for_status()
        return r.json()

    # Define Media Endpoints
    def query_media_data(self, query: MediaQuery):
        """http://docs.data-api.boulderai.com/#query-media-data"""
        print(f'Query => {query.toJSON()}')
        r = requests.post(f'{self.api_base}media/query', data=query.toJSON(), headers=self.headers)
        r.raise_for_status()
        return r.json()

    def __init__(self, api_key: str, api_base: str = 'https://data-api.boulderai.com/'):
        self.api_key = api_key
        self.api_base = api_base
        self.set_headers()
