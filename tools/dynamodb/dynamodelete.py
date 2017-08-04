'''
    author: Chandra Krintz
    Delete all items from a dynamodb table
    LICENSE: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE
'''
import boto3,argparse,sys
from pprint import pprint

def main():
    # parse args
    parser = argparse.ArgumentParser(description="Simple DynamoDB Delete-All Script")
    parser.add_argument('tableName',action='store',help='DynamoDB table to delete all items from')
    parser.add_argument("--profile","-p",default=None, help="AWS credentials file profile to use. Allows you to use a profile instead accessKey, secretKey authentication")
    parser.add_argument('--region','-r',action='store',default='us-west-2',help='AWS Region table is in')
    args = parser.parse_args()

    profile = args.profile
    aws_region = args.region
    tableName = args.tableName
    if profile:
        boto3.setup_default_session(profile_name=profile)

    client = boto3.client('dynamodb', region_name=aws_region)
    dynamodb = boto3.resource('dynamodb',region_name=aws_region)
    table = dynamodb.Table(tableName)
    response = client.describe_table(TableName=tableName)

    keys = [k['AttributeName'] for k in response['Table']['KeySchema']]
    response = table.scan()
    items = response['Items']
    number_of_items = len(items)
    if number_of_items == 0:  # no items to delete
        print("Table '{}' is empty.".format(tableName))
        return
    with table.batch_writer() as batch:
        count = 0
        for item in items:
            key_dict = {k: item[k] for k in keys}
            #print("Deleting " + str(item) + "...")
            count += 1
            batch.delete_item(Key=key_dict)
        print("Deleted {} items".format(count))

if __name__ == "__main__":
    main()
