import json,argparse,sys,pprint
from subprocess import PIPE, run

DEBUG = False
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser')
    parser.add_argument('awsprofile',action='store',help='aws profile to use')
    parser.add_argument('region',action='store',help='aws region to use')
    parser.add_argument('lambdas',action='store',help='list of colon delimited prefix names for all of the lambda functions that you wish to remove the events for')
    args = parser.parse_args()

    #command = ['ls', '-l', 'ns']
    #result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    #print(result.returncode, '\n', result.stdout, '\n', result.stderr)

    pp = pprint.PrettyPrinter(indent=2)
    command = ['aws', 'lambda', 'list-event-source-mappings','--profile',args.awsprofile,'--region',args.region]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if result.returncode != 0:
        print('ERROR in command: {}\n{}'.format(result.returncode,result.stderr))
        sys.exit(1)
    event_info = json.loads(result.stdout)
    if DEBUG:
        pp.pprint(event_info)

    fns = args.lambdas.split(':')
    for esm in event_info['EventSourceMappings']:
        uuid = esm['UUID']
        state = esm['State']
        arn = esm['FunctionArn']

        idx = arn.find(':function:')
        fname = arn[idx+10:]
        if fname in fns:
            print('removing event source {} for Lambda function {}'.format(uuid,fname))
            command = ['aws', 'lambda', 'delete-event-source-mapping','--profile',args.awsprofile,'--region',args.region, '--uuid', uuid]
            result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if result.returncode != 0:
                print('ERROR in delete command: {}\n{}'.format(result.returncode,result.stderr))
                sys.exit(1)
         

