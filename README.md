# data-api-utils

Utilities for working with the Sighthound [Data API](http://docs.data-api.boulderai.com/#introduction)

# Setup

```
pip3 install -r requirements.txt
```
## Instructions and examples

Run `python3 data-apy.py --help` for an overview.

### Arguments  
#### Required Arguments:   
- `--key=${API_KEY}`: API Key obtained from the Sighthound/Boulder AI Platform  
- `--deviceId`: the deviceId of the device you would like to query  
- `--sensors`: a comma separated list of the sensors you would like to query  

### Optional Arguments
- `--crossReferenceSensor`: A sensor to cross reference events with. The cross referenced sensor's time and time difference relative to original sensor will be included in the CSV file if `--csv` is specified.

#### Timeframe Arguments - at least one required:  
- `--startTime`: The start time you would like to query from, accepts any format that dateutil.parser supports
	- Optional and not used if --lastHours or --lastDays is specified  
- `--endTime`: The end time that you would like to query to  
	- If not specified, set to now  
- `--lastDays`: A number of days relative to endTime (or now if endTime is not specified) to query from  
- `--lastHours`: A number of hours relative to endTime (or now if endTime is not specified) to query from  

#### Filters:  
- `--filterMinutesModulo`: An optional modulo filter. When specified with filterMinutesRestrict this filters out events which occurred outside periods defined by a modulus of the minute of event for instance, specifying --filterMinutesModulo 10 and --filterMinutesRestrict 3 would include events which happened during the first 3 minutes of every 10 minute interval, starting at the top of the hour.                                                                                        
- `--filterMinutesRestrict`: An optional restrict filter. See notes for filterMinutesModulo

#### Download Clips:
**Note: To download clips you must be [logged into a Google User account](https://cloud.google.com/sdk/gcloud/reference/auth/login) with read access to the bai-rawdata bucket. Login with `gcloud auth application-default login`.**
- `--downloadEventClips`: Optional flag to download the video clips of the queried events if they exist in the bai-rawdata GCP bucket
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
Query data for collision sensor on BAI_0000754 for the last 5 hours:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=5
```
Query data for collision sensor on BAI_0000754 for the last 5 hours, cross reference these events with PRESENCE_SENSOR_1 and create a CSV file at out.csv:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=5 --crossReferenceSensor PRESENCE_PERSON_1 --csv 
```
Query data for collision sensor on BAI_0000754 for a specific date range:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --startTime=2021-07-20T16:49:41 --endTime=2021-07-22T16:49:41
```
Query data for collision sensor on BAI_0000754 for the last day, filtering on events which occurred in the first 5 minutes of any 10 minute interval:
```
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastDay=1 --filterMinutesModulo=10 --filterMinutesRestrict=5
```
Download clips of all collision events in the last hour from GCP base path bai-rawdata/gcpbai (default) to local output folder ./output/:
```
gcloud auth application-default login
mkdir output
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=1 --filterMinutesModulo=10 --filterMinutesRestrict=5 --downloadEventClips --sourceGCPpath bai-rawdata/gcpbai --output output/
```

Download event clips of all collision events in the last hour from GCP bucket base path bai-rawdata/gcpbai/ , upload event clips to GCP bucket bai-dev-data/ai-analysis/sample, and save a CSV file out.csv with links to the clips:
```
gcloud auth application-default login
mkdir output
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=1 --filterMinutesModulo=10 --filterMinutesRestrict=5 --downloadEventClips --sourceGCPpath bai-rawdata/gcpbai  --output output/ --uploadEventClips bai-dev-data/ai-analysis/sample/ --csv out.csv
```

Download event clips of all collision events in the last hour from GCP bucket base path bai-rawdata/gcpbai/ , upload event clips to GCP bucket bai-dev-data/ai-analysis/sample, and save a CSV file out.csv with links to the clips. 
Additionally, cross reference these events with PRESENCE_PERSON_1 events and have this information included in the CSV file.:
```
gcloud auth application-default login
mkdir output
python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000754 --lastHour=1 --filterMinutesModulo=10 --filterMinutesRestrict=5 --downloadEventClips --sourceGCPpath bai-rawdata/gcpbai  --output output/ --uploadEventClips bai-dev-data/ai-analysis/sample/ --crossReferenceSensor PRESENCE_PERSON_1 --csv out.csv
```


