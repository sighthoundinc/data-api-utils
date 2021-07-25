import argparse
import datetime
import json

import requests
import dateutil.parser
import dateutil.tz
import pprint
import textwrap


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


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    sensor_query()
