# data-api-utils

Utilities for working with the Sighthound [Data API](http://docs.data-api.boulderai.com/#introduction)

## Setup

```
pip3 install -r requirements.txt
```

# Instructions and examples
There are a few different example scripts in this repository that can be used to demonstrate the capabilities of the Sighthound Data API:
## src/find_media_by_sensor.py
Run `python3 src/find_media_by_sensor.py --help` for an overview. The `find_media_by_sensor.py` script can be used to query the videos associated with the last 10 sensor events for a specific sensor and stream. For each event, gsutil URI's will be provided for video events. See the [gsutil documentation](https://cloud.google.com/storage/docs/gsutil) for information on how you can download the videos using the gsutil URIs.
### Required Arguments/Environment Variables
- `export API_KEY=<API_KEY>`: The `API_KEY` environment variable must be set with your Sighthound Data API Key prior to running this script
- `--stream_id`: The stream_id that you would like to query events for. If using a DNNCam, use the device ID (i.e. BAI_0000134). Else, query for sensors on a device to get associated streamId's, see https://docs.data-api.sighthound.com/#get-sensors-by-device
- `--sensors`: The sensor(s) to be queried. These should be formatted as `<streamUUID>__<sensorName>` where the `streamUUID` should be `0` for DNNCam's. For example, if you would like to view the events from the `PRESENCE_PERSON_1` sensor on a DNNCam, the sensor name would be `0__PRESENCE_PERSON_1`.

### Examples
Query media events for the last 10 `PRESENCE_PERSON_1` events on camera BAI_0000134
```
export API_KEY="38ed7729792c48489945c8060255fa45"
python3 src/find_media_by_sensor.py --stream_id BAI_0000134 --sensors 0__PRESENCE_PERSON_1
```

## src/device_status_check.py
Run `python3 src/device_status_check.py --help` for an overview. The `device_status_check.py` script can be used 
to get a quick overview of the status of the devices in a given workspace. It will report the status of services 
running on devices in a workspace, as well as any devices that have > 90% storage used.  
### Required Arguments/Environment Variables
- `export API_KEY=<API_KEY>`: The `API_KEY` environment variable must be set (or populated in a `.env` file) with your Sighthound Data API Key prior
to running the script
- `--workspace_id`: The workspace ID of the workspace of devices you'd like to query.
### Optional Arguments:
- `--device_list`: A JSON file of a list of devices that you would like to get the status of. Please note that only devices
that belong to the workspace (specified by the `--workspace_id` parameter) and are in the list will be reported. Please see
the [cust_devices.json](cust_devices.json) as an example/template file. 

### Examples
Query the device status of the devices in the `cust_devices.json` file that are in the workspace with workspace ID `9cc77d13-5381-479d-b805-0472c97d4055`.
```
export API_KEY="38ed7729792c48489945c8060255fa45"
python3 src/device_status_check.py --workspace_id 9cc77d13-5381-479d-b805-0472c97d4055 --device_list cust_devices.json"
```

## data-api.py
Run `python3 data-api.py --help` for an overview. The `data-api.py` script can be used to do simple data queries with a device and sensor name.  This script can also be used to download event clips if the device is setup to record using the Data Acquisition container. (Data Acquisition is the legacy implementation and the `find_media_by_sensor.py` script should be used to query event clips with the stream API's)

#### Required Arguments
- `--API_KEY=<API_KEY>`: the API key to be used
- `--deviceId`: the deviceId of the device you would like to query
- `--sensors`: a comma separated list of the sensors you would like to query
#### Timeframe Arguments - at least one required:
- `--startTime`: The start time you would like to query from, accepts any format that dateutil.parser supports
	- Optional and not used if --lastHours or --lastDays is specified
- `--endTime`: The end time that you would like to query to
	- If not specified, set to now
- `--lastDays`: A number of days relative to endTime (or now if endTime is not specified) to query from
- `--lastHours`: A number of hours relative to endTime (or now if endTime is not specified) to query from
#### Download Clips:
Note: To download clips you must be [logged into a Google User account](https://cloud.google.com/sdk/gcloud/reference/auth/login) with read access to the specified bucket (see "Accessing Device Media" below). Login with `gcloud auth application-default login`. Note that this is the legacy implementation and requires that
the Data Acquisition container is uploading footage.
- `--downloadEventClips`: Optional flag to download the video clips of the queried events if they exist in a user-accessible GCP bucket.
	- Must be used with the `--output` flag
- `--output`: The output directory to download the event clips to
- `--sourceGCPpath`: Google Cloud Storage path to search for and retrieve video clips from. Should be in the format `<bucket>/pathTo/deviceDirs`. If not specified, will default to `bai-rawdata/gcpbai/`
- `--uploadEventClips`: Google Cloud Storage path to upload event clips to. Should be in the format `<bucket>/pathTo/eventClips/`. If specified, the event clips will be deleted locally after upload.
	- `--csv` argument can be used with `--uploadEventClips`
- `--csv`: Path to output CSV file with eventId, timeCollected, and event clip GCP link if `--uploadEventClips` is specified.

### Examples:
Query data for collision sensor on BAI_0000754 for the last 3 days:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastDay=3
```
Query data for collision sensor on BAI_0000754 for a specific date range:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --startTime=2021-07-20T16:49:41 --endTime=2021-07-22T16:49:41
```
Query data for collision sensor on BAI_0000754 for the last 5 hours, cross reference these events with PRESENCE_SENSOR_1 and create a CSV file at out.csv:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=5 --crossReferenceSensor PRESENCE_PERSON_1 --csv
```

# Acessing Device Media
The Sighthound support team can set up a GCP bucket for customers to be able to view the images, video, and event clips being uploaded from a DNN-Cam or DNN-Node device. Customers will be authenticated via their Google User account and the user must log in with `gcloud auth application-default login`  (see [Installing Cloud SDK](https://cloud.google.com/sdk/docs/install)) to access the clips using this script. Please reach out to the Sighthound team if you would like this set up.

The bucket name will generally be `sh-ext-<customer>` and bucket structure looks like:
```
sh-ext-<customer>       -- Base directory contains one directory for each device
├── BAI_0000649
│   ├── data_acq_pic	-- Images collected by the Data Acquisition container
│   |	├── 2021-04-22  -- Images are sorted by date
│   |	|	└── ...
│   |	└── 2021-11-02
│   |		└── ...
│   └── data_acq_vid	-- Videos collected by the Data Acquisition container
│   	├── 2021-04-22  -- Videos are sorted by date
│   	|	└── ...
│   	└── 2021-11-02
│   		└── ...
├── BAI_0001049
│   ├── data_acq_pic
│   |	└── ...
│   └── data_acq_vid
│   	└── ...
└── ...
```

# Contributing source changes

Thanks for your contribution!  Please see [CONTRIBUTING.md](CONTRIBUTING.md) for instructions.
