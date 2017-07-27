import boto3,json,botocore,argparse

def runit(profile,rn,rp):
    if profile:
        boto3.setup_default_session(profile_name='cjk1')
    client = boto3.client('iam')

    trust_role = {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "",
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    
    try:
        response = client.create_role(RoleName=rn,AssumeRolePolicyDocument=json.dumps(trust_role))
        print(response['Role']['Arn'])
        print("Success: done creating role {}".format(rn))
    except botocore.exceptions.ClientError as e:
        print("Error: {0}".format(e))
    
    try:
        with open('policy.json') as json_data:
            response = client.put_role_policy(RoleName=rn,PolicyName=rp,
                PolicyDocument=json.dumps(json.load(json_data))
            )
            print("Success: done adding inline policy to role {}".format(rp))
    except botocore.exceptions.ClientError as e:
        print("Error: {0}".format(e))
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='create-role')
    parser.add_argument('--profile','-p',action='store',default=None,help='AWS profile to use, omit argument if none')
    parser.add_argument('role_name',action='store',help='Role name to create or update')
    parser.add_argument('policy_name',action='store',help='Policy name to create or update')
    args = parser.parse_args()
    runit(args.profile,args.role_name,args.policy_name)

