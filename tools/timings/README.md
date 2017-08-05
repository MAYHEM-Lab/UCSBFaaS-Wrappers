# Tools to collect timings with and without spotwrap

Pass into each bash script your AWS account ID and your AWS profile, e.g. ```./mr.sh XXXACCTXXXX awsprofile1```.

cleanup.sh deletes all files, logs, and database entries.  Use this with caution.  You may need to run this multiple times until all of the running jobs complete and write out their data and logs (e.g. if you stopped/killed a job midstream!)... until you see ```Table 'spotFns' is empty.``` repeatedly, keep retrying after some time delay.

overhead.sh runs the map/reduce job with SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapper, reducer, reducerCoordinator, and driver (set in setupconfig.json for setupApps.py installation).

overheadNS.sh runs the map/reduce job without SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapperNS, reducerNS, reducerCoordinatorNS, and driverNS (set in setupconfig.json for setupApps.py installation).

mr.sh runs the SpotWrap map-reduce job in lambda and collects its output data from cloudwatch and the database.
