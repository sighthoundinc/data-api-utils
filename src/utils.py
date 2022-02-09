import datetime


def get_media_range(event_start: datetime, look_back: int = 15, look_forward: int = 15):
    return event_start - datetime.timedelta(minutes=look_back), event_start + datetime.timedelta(minutes=look_forward)
