'''
    author: Chandra Krintz
    Download cloudwatch logs, delete from AWS once downloaded
    LICENSE: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE
'''
import boto3,argparse,sys,time
from pprint import pprint
from datetime import datetime
from datetime import timezone

############ main ##################
def main():
    # parse args
    parser = argparse.ArgumentParser(description="Convert timestamps to datetime strings and vice versa")
    parser.add_argument('ts',action='store',help='# milliseconds since epoch (Cloudwatch ts) OR datetime in string (format=Y-m-d H:M:S), use either toEpoch or toDT (not both) to indicate which')
    parser.add_argument('--toEpoch',action='store_true',default=False,help='convert Y-m-d H:M:S to epoch (secs)')
    parser.add_argument('--toDT',action='store_true',default=False,help='convert epoch to Y-m-d H:M:S')
    parser.add_argument('-s',action='store_true',default=False,help='epoch passed in uses # seconds since epoch instead of # of millis (this option only works if --toDT is used.')
    args = parser.parse_args()
    toEpoch = args.toEpoch
    toDT = args.toDT
    if not toEpoch and not toDT:
        print('One of --toEpoch and --toDT must be set')
        sys.exit(1)
    if toEpoch and toDT:
        print('Both --toEpoch and --toDT cannot be set at the same time')
        sys.exit(1)
    if toDT:
        try:
            ts = float(args.ts)
        except:
            print('Unable to convert timestamp to float, please retry with a long int value')
            sys.exit(1)
        if not args.s:
            ts = ts/1000
        ts1 = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))
        print("GMT: {}".format(ts1))
        ts1 = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
        print("Local: {}".format(ts1))
        #ts1 = datetime.fromtimestamp(ts).strftime('%c')
        #print("DT: {}".format(ts1)) #same as local above
    else:
        try:
            dt = datetime.strptime(args.ts, '%Y-%m-%d %H:%M:%S')
        except:
            print('Unable to convert string to datetime, please retry with using the format "%Y-%m-%d %H:%M:%S"')
            sys.exit(1)
        ts = dt.replace(tzinfo=timezone.utc).timestamp()
        print("GMT Epoch: {}secs {}msecs".format(ts,ts*1000))
        ts = dt.timestamp()
        print("Local Epoch: {}secs {}msecs".format(ts,ts*1000))

if __name__ == "__main__":
    main()
