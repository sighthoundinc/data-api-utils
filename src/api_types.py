import datetime
import json
from enum import Enum
from typing import List
import humps


class JsonObject:

    def toJSON(self):
        def del_none(d):
            """
            Delete keys with the value ``None`` in a dictionary, recursively.

            This alters the input so you may wish to ``copy`` the dict first.
            """
            # For Python 3, write `list(d.items())`; `d.items()` won’t work
            # For Python 2, write `d.items()`; `d.iteritems()` won’t work
            for key, value in list(d.items()):
                if value is None:
                    del d[key]
                elif isinstance(value, dict):
                    del_none(value)
            return d  # For convenience

        def transform_dict(d):
            if isinstance(d, list):
                return [transform_dict(i) if isinstance(i, (dict, list)) else i for i in d]
            return {humps.camelize(a): transform_dict(b) if isinstance(b, (dict, list)) else b for a, b in d.items()}

        def json_default(value):
            if isinstance(value, datetime.date):
                return value.isoformat()
            elif isinstance(value, Enum):
                return value.name
            else:
                return transform_dict(del_none(value.__dict__))

        return json.dumps(self, default=json_default, sort_keys=True, indent=4)


class InProgressEvents(Enum):
    NONE = 1
    INCLUDE = 2
    ONLY = 3


class StreamQuery(JsonObject):
    """

    """

    stream_id: str
    device_id: str
    sensors: List[str]
    start_time: datetime
    end_time: datetime
    limit: int
    order: str
    with_meta: bool
    in_progress_events: InProgressEvents

    def __init__(self,
                 stream_id: str,
                 sensors: List[str],
                 start_time: datetime,
                 end_time: datetime,
                 limit: int = None,
                 order: str = None,
                 with_meta: bool = None,
                 in_progress_events: InProgressEvents = None,
                 device_id: str = None,
                 ):
        self.stream_id = stream_id
        self.device_id = device_id
        self.sensors = sensors
        self.start_time = start_time
        self.end_time = end_time
        self.limit = limit
        self.order = order
        self.with_meta = with_meta
        self.in_progress_events = in_progress_events


class StreamQueryAggregate(JsonObject):
    """

    """

    stream_id: str
    device_id: str
    sensors: List[str]
    start_time: datetime
    end_time: datetime
    interval: str
    functions: List[str]
    fill_empty_windows: bool
    order: str

    def __init__(self,
                 stream_id: str,
                 device_id: str,
                 sensors: List[str],
                 start_time: datetime,
                 end_time: datetime,
                 interval: str,
                 functions: List[str],
                 fill_empty_windows: bool,
                 order: str
                 ):
        self.stream_id = stream_id
        self.device_id = device_id
        self.sensors = sensors
        self.start_time = start_time
        self.end_time = end_time
        self.interval = interval
        self.functions = functions
        self.fill_empty_windows = fill_empty_windows
        self.order = order


class MediaQuery(JsonObject):
    """

    """

    stream_id: str
    start_time: datetime
    end_time: datetime
    media_type: str

    def __init__(self,
                 stream_id: str,
                 start_time: datetime,
                 end_time: datetime,
                 ):
        self.stream_id = stream_id
        self.start_time = start_time
        self.end_time = end_time
        self.media_type = 'VIDEO'


class SensorsByWorkspaceQuery(JsonObject):
    """

    """

    workspace_id: str
    start_time: datetime
    end_time: datetime

    def __init__(self,
                 workspace_id: str,
                 start_time: datetime,
                 end_time: datetime,
                 ):
        self.workspace_id = workspace_id
        self.start_time = start_time
        self.end_time = end_time


class LatestSensorEventQuery(JsonObject):
    """

    """

    stream_id: str
    sensor_id: str

    def __init__(self,
                 stream_id: str,
                 sensor_id: str,
                 ):
        self.stream_id = stream_id
        self.sensor_id = sensor_id
