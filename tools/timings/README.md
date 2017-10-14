# Tools to collect timings for GammaRay and example multi-function Lambda applications

GammaRay is an AWS Lambda extension that uses Fleece/XRay to collect timings
of functions and the API/SDK calls they make and adds support for capturing
causal order across functions, across regions, and through AWS services.

The default configuration used in the scripts is B = GammaRay.  Other configurations are possible (see the scripts), including    
C=clean (no gammaray tracing)      
T=clean with X-ray tracing on   
F=x-ray tracing on and fleece support (x-ray daemon)
S=static profiling configuration (slow)
D=dynamic profiling configuration (slow)

To run any of these jobs, go through all of the steps in ../RUN\_README

To get started quickly and just do a test run, implement the steps in the
GammaRay demo located in the README.md here: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/tree/master/gammaRay 

**cleanupAWS.sh** deletes all files, logs, database entries, and all outputs from \*.sh timings.  Use this with caution.  Edit the file to add deletion of local results files (see commented lines at end of file)

**overheadMR.sh** repeatedly runs the map/reduce job (synchronous/original implementation) 
Possible tests (capital letter suffix) are S=static gammaray (original spotwrap)   
C=clean (no gammaray or spotwrap or tracing)   
T=clean with X-ray tracing on   
F=x-ray tracing on and fleece support (x-ray daemon)
G=gammaray support (dynamic gammaray via fleece extensions; x-ray tracing should be turned off)

**mr.sh** runs the GammaRay map-reduce job in lambda (asynchronous mode) and collects its output data from cloudwatch and the database. 

**webapp.sh** runs the GammaRay web app in lambda (asynchronous mode) and collects its output data from cloudwatch and the database. 

**imageProc.sh** runs the GammaRay image processing in lambda and collects its output data from cloudwatch and the database. 

**micro.sh** runs the GammaRay and Clean microbenchmarks lambda and collects its output data from cloudwatch and the database. 

**Please NOTE:**   
The map-reduce output can differ across runs because the coordinator may invoke
the reducer multiple times (depending upon when it is triggered by mapper writes and when
all mappers complete).  This will cause differences in the output.

