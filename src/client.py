from api_types import *
import requests


class DataApiClient:
    """Data API Client"""
    api_base: str
    api_key: str
    headers: dict

    def set_headers(self):
        self.headers = {'Content-type': 'application/json', 'X-API-Key': f'{self.api_key}'}

    # Define Stream Endpoints
    def get_latest_stream_event(self, query: LatestSensorEventQuery):
        """http://docs.data-api.boulderai.com/#get-latest-stream-data"""
        r = requests.get(
            f'{self.api_base}data/stream/{query.stream_id}/latest?sensorId={query.sensor_id}',
            headers=self.headers)
        r.raise_for_status()
        return r.json()

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

    def query_status_by_workspace(self, query: LatestStatusByWorkspaceQuery):
        """https://storage.googleapis.com/bai-data-api-docs/index.html#get-latest-status-by-workspace"""
        r = requests.get(
            f'{self.api_base}workspace/{query.workspace_id}/devices/status',
            headers=self.headers
        )
        r.raise_for_status()
        return r.json()

    def query_sensors_by_device(self, query: SensorsByDeviceQuery):
        """https://storage.googleapis.com/bai-data-api-docs/index.html#get-sensors-by-device"""
        r = requests.get(
            f'{self.api_base}device/{query.device_id}/sensors?startTime={query.start_time}&endTime={query.end_time}',
            headers=self.headers
        )
        r.raise_for_status()
        return r.json()

    def __init__(self, api_key: str, api_base: str = 'https://data-api.boulderai.com/'):
        self.api_key = api_key
        self.api_base = api_base
        self.set_headers()
