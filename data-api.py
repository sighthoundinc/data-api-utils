import argparse
import datetime
import json

import requests
import dateutil.parser
import dateutil.tz
import pprint
import textwrap
import sys, os, subprocess
import re
from google.cloud import storage
import google.auth
import ffmpeg
import shutil

VIDEO_LENTH_MINUTES = 5
SECONDS_BEFORE_EVENT = 10
SECONDS_AFTER_EVENT = 5

def query_flat(args):
    url = 'https://data-api.boulderai.com/data/sensor/query'
    headers = {'Content-type': 'application/json', 'X-API-Key': f'{args.key}'}
    data = {'deviceId': f'{args.deviceId}',
            'sensors': [f'{args.sensors}'],
            'startTime': f'{args.startTime}',
            'endTime': f'{args.endTime}'}
    print(f'Issuing curl "{url}" -d \'{{"deviceId":"{args.deviceId}","sensors":["{args.sensors}"],'
          f'"startTime":"{args.startTime}","endTime":"{args.endTime}"}}\' \\\n'
          f'-X POST \\\n'
          f'-H "Content-Type: application/json" \\\n'
          f'-H "X-API-KEY: {args.key}"')
    r = requests.post(url, data=json.dumps(data), headers=headers)
    r.raise_for_status()
    return r.json()


def time_parse(args, parser):
    format_str = "%Y-%m-%dT%H:%M:%S.000Z"
    if args.startTime is not None:
        passed_start_time = args.startTime
        start_date = dateutil.parser.parse(args.startTime)
        args.startTime = start_date.astimezone(dateutil.tz.UTC).strftime(format_str)
        print(f'converted start time {passed_start_time} to UTC time value {args.startTime}')
    if args.endTime is not None:
        passed_end_time = args.endTime
        end_date = dateutil.parser.parse(args.endTime)
        args.endTime = end_date.astimezone(dateutil.tz.UTC).strftime(format_str)
        print(f'converted end time {passed_end_time} to UTC time value {args.endTime}')
    else:
        args.endTime = datetime.datetime.now().astimezone(dateutil.tz.UTC).strftime(format_str)
        end_date = dateutil.parser.parse(args.endTime)
        print(f'endTime not specified, using time now ({args.endTime})')
    if args.lastDays is not None:
        args.startTime = (end_date - datetime.timedelta(days=args.lastDays)).strftime(format_str)
        print(f'lastDays {args.lastDays} specified, used this to set startTime to {args.startTime}')
    if args.lastHours is not None:
        args.startTime = (end_date - datetime.timedelta(hours=args.lastHours)).strftime(format_str)
        print(f'lastHours {args.lastHours} specified, used this to set startTime to {args.startTime}')

    if args.startTime is None or args.endTime is None:
        print(f'Time range not specified for query')
        parser.print_help()
        raise ValueError('Invalid arguments')

def findVideo(gcp_client, args, time):
    basePrefix = f"gcpbai/{args.deviceId}/"
    prefix = basePrefix + time.strftime("%Y-%m-%d") + "/"
    blobs = gcp_client.list_blobs("bai-rawdata", prefix=prefix)
    format_str = "DataAcqVideo_%Y-%m-%d-%H-%M-%S.%f"
    after_time = time - datetime.timedelta(minutes=VIDEO_LENTH_MINUTES)
    # search for matching video
    for blob in blobs:
        video_name = re.search("DataAcqVideo_.*mp4", blob.name)
        if video_name:
            video_time = datetime.datetime.strptime(video_name.group(0).replace(".mp4", "000"), format_str).replace(tzinfo=dateutil.tz.UTC)
            if video_time > after_time and video_time < time:
                return blob
    return False

def trim(start,end,input,output):
    (
        ffmpeg
        .input(input)
        .trim(start=start, end=end)
        .output(output)
        .overwrite_output()
        .run(quiet=True)
    )
            
def downloadClip(gcp_client, args, event, video_blob):
    # create tmp directory if it doesn't exist already
    if not os.path.isdir(args.output + "/tmp/"):
        os.mkdir(args.output + "/tmp/")
    tmp_filename = args.output + "/tmp/" + video_blob.name.split('/')[-1] 
    # download file if it doesn't exist already
    if not os.path.isfile(tmp_filename):
        with open(tmp_filename, "+w"):
            video_blob.download_to_filename(tmp_filename)
    # find cooresponding time in video
    event_time = dateutil.parser.parse(event['timeCollected']).astimezone(dateutil.tz.UTC)
    video_name = re.search("DataAcqVideo_.*mp4", video_blob.name)
    format_str = "DataAcqVideo_%Y-%m-%d-%H-%M-%S.%f"
    video_time = datetime.datetime.strptime(video_name.group(0).replace(".mp4", "000"), format_str).replace(tzinfo=dateutil.tz.UTC)
    video_relative_time = event_time - video_time
    format_str = "%H:%M:%S"
    start_time = str(video_relative_time - datetime.timedelta(seconds=SECONDS_BEFORE_EVENT))
    end_time = str(video_relative_time + datetime.timedelta(seconds=SECONDS_AFTER_EVENT))
    # make sure we're not going out of bounds
    if datetime.timedelta(seconds=SECONDS_BEFORE_EVENT) > video_relative_time:
        start_time = "00:00:00.000"
    if (video_relative_time + datetime.timedelta(seconds=SECONDS_AFTER_EVENT)) > datetime.timedelta(seconds=VIDEO_LENTH_MINUTES*60):
        end_time = f"00:0{VIDEO_LENTH_MINUTES}:00"
    # trim the video using ffmpeg
    output_filename = args.output + "/" + event['id'] + ".mp4"
    trim(start_time, end_time, tmp_filename, output_filename)
    return output_filename


def sensor_query():
    parser = argparse.ArgumentParser(description="Data API query tool for the Sigthhound Data API",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent('''\
    Examples:
    Query data for collision sensor on BAI_000646 for the last 3 days:
        python data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000646 --lastDay=3
    Query data for collision sensor on BAI_000646 for the last 5 hours:
        python data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000646 --lastHour=5
    Query data for collision sensor on BAI_000646 for a specific date range:
        python data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000646 \
            --startTime=2021-07-20T16:49:41 --endTime=2021-07-22T16:49:41
    Query data for collision sensor on BAI_000646 for the last day, filtering on events which occurred
    in the first 5 minutes of any 10 minute interval:
        python data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000646 --lastDay=1 \
            --filterMinutesModulo=10 --filterMinutesRestrict=5
    Download clips of all collision events in the last hour to output folder ./output/:
        python3 data-api.py --key=${API_KEY} --sensors=COLLISION_1 --deviceId=BAI_0000646 --lastHour=1 \
            --filterMinutesModulo=10 --filterMinutesRestrict=5 --downloadEventClips --output output/
    '''))
    parser.add_argument('--sensors', help="A comma separated list of sensors to query")
    parser.add_argument('--deviceId', help="The device ID (BAI_XXXXXXX)")
    parser.add_argument('--lastHours',
                        type=int,
                        help="A number of hours relative to endTime (or now if endTime is not specified) to query")
    parser.add_argument('--lastDays',
                        type=int,
                        help="A number of days relative to endTime (or now if endTime is not specified) to query")
    parser.add_argument('--startTime',
                        help="The start time, accepted in any format dateutil.parser supports.  Optional and not used"
                             "if --lastHours aor --lastDays is specified")
    parser.add_argument('--endTime',
                        help="The end time, accepted in any format dateutil.parser supports.\n"
                             "see https://dateutil.readthedocs.io/en/stable/examples.html#parse-examples.\n"
                             "If not specified, set to now")
    parser.add_argument('--key',
                        help="The API key for the workspace associated with the device (available from the platform)")
    parser.add_argument('--filterMinutesModulo', type=int,
                        help='An optional modulo filter.  When specified with filterMinutesRestrict this filters\n'
                             'out events which occurred outside periods defined by a modulus of the minute of event\n'
                             'for instance, specifying --filterMinutesModulo 10 and --filterMinutesRestrict 3 would\n'
                             'include events which happened during the first 3 minutes of every 10 minute interval,\n'
                             'starting at the top of the hour.')
    parser.add_argument('--filterMinutesRestrict', type=int,
                        help='An optional restrict filter.  See notes for filterMinutesModulo')
    parser.add_argument('--downloadEventClips', action='store_true',
                        help='An optional argument to download the video clips of the events if they exist in the bai-rawdata\n'
                             'GCP bucket. Must be used with --output flag. ')
    parser.add_argument('-o', '--output',
                        help='Directory to download event clips. To be used with --downloadEventClips flag.')
    args = parser.parse_args()

    time_parse(args, parser)
    result = query_flat(args)
    if args.filterMinutesModulo and args.filterMinutesRestrict:
        print(f"Events filtered for the first {args.filterMinutesRestrict} minutes of each "
              f"{args.filterMinutesModulo} minute interval")
        filtered_result = []
        for event in result:
            minutes = dateutil.parser.parse(event['timeCollected']).timetuple().tm_min
            if minutes % args.filterMinutesModulo < args.filterMinutesRestrict:
                filtered_result.append(event)
    else:
        filtered_result = result
    start_date = dateutil.parser.parse(args.startTime).astimezone(dateutil.tz.tzlocal())
    end_date = dateutil.parser.parse(args.endTime).astimezone(dateutil.tz.tzlocal())
    print(f"Starting at {args.startTime} (local time {start_date}) "
          f"and ending {end_date - start_date} later at {args.endTime} (local time {end_date})")
    pprint.pprint(filtered_result)
    # download clips if video exists
    if args.downloadEventClips:
        if not args.output:
            print("ERROR: must pass --output flag with --downloadEventClips")
            sys.exit(1)
        if not os.path.isdir(args.output):
            print(f"ERROR: {args.output} is not a directory!")
            sys.exit(1)

        format_str = "%Y-%m-%dT%H:%M:%S.000Z"
        # initialize gcp client
        gcp_client = None
        try:
            credentials, project = google.auth.default()
            gcp_client = storage.Client(project, credentials)
        except:
            print(f"Failed opening GCP storage client, please login using `gcloud auth application-default login`")
            sys.exit(1)

        i = 0
        for event in filtered_result:
            # if i > 0:
            #     continue
            event_time = dateutil.parser.parse(event['timeCollected']).astimezone(dateutil.tz.UTC)
            print(f"Searching for video for event with ID {event['id']}... ", end="", flush=True)
            video_blob = findVideo(gcp_client, args, event_time)
            if video_blob == False:
                print("No luck.")
                continue
            else:
                print("Found!")
            filename = downloadClip(gcp_client, args, event, video_blob)
            print(f"Downloaded {filename}")
            i += 1 
        # clear up tmp files
        shutil.rmtree(args.output + "/tmp/")

    return filtered_result


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    result = sensor_query()

