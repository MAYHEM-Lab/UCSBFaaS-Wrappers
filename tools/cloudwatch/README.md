# Cloudwatch logs download tool
Get and write out the log files (processing messages with REPORT and SpotWrap substrings only) fro AWS Cloudwatch  
requirements: python3, boto3
```
#timestamp epochs must be milliseconds since epoch (not seconds!)
#give a start date some time in past as epoch (or string datetime in this format: "%Y-%m-%d %H:%M:%S")
python downloadLogs.py "/aws/lambda/FNAME" 1401861965497 -p awsprofile > FNAME.log
#give start and end timestamp (or datetime string)
python downloadLogs.py "/aws/lambda/FNAME" 1401861965497 1501861965497 -p awsprofile > FNAME.log
```

# Timestamp conversion tool
```
#timestamp epochs must be milliseconds since epoch (not seconds, else use -s to use seconds)
python convertTime.py "1501861965497" --toDT
#Also reverse
python convertTime.py "2017-08-04 15:57:00" --toEpoch
```
