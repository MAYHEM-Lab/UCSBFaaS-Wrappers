# Tools to collect timings with and without spotwrap

Edit each bash script and change XXX to your AWS account ID and YYY to your AWS profile.

cleanup.sh deletes all files, logs, and database entries.  Use this with caution.

overhead.sh runs the map/reduce job with SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapper, reducer, reducerCoordinator, and driver (set in setupconfig.json for setupApps.py installation).

overheadNS.sh runs the map/reduce job without SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapperNS, reducerNS, reducerCoordinatorNS, and driverNS (set in setupconfig.json for setupApps.py installation).
