import boto3,botocore,argparse

def runit(profile,rn,rp):
    if profile:
        boto3.setup_default_session(profile_name='cjk1')
    client = boto3.client('iam')

    try:
        response = client.delete_role_policy(RoleName=rn,PolicyName=rp)
        print("Success: done deleting role policy {} for role {}".format(rp,rn))
    except botocore.exceptions.ClientError as e:
        print("Error: {0}".format(e))
 
    try:
        response = client.delete_role(RoleName=rn)
        print("Success: done deleting role {}".format(rn))
    except botocore.exceptions.ClientError as e:
        print("Error: {0}".format(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='delete-role')
    parser.add_argument('--profile','-p',action='store',default=None,help='AWS profile to use, omit argument if none')
    parser.add_argument('role_name',action='store',help='Role name to create or update')
    parser.add_argument('policy_name',action='store',help='Policy name to create or update')
    args = parser.parse_args()
    runit(args.profile,args.role_name,args.policy_name)
