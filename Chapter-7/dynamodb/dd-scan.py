import boto3
from boto3.dynamodb.conditions import Key, Attr

AWS_KEY="<enter>"
AWS_SECRET="<enter>"
REGION="us-east-2"

dynamodb = boto3.resource('dynamodb', aws_access_key_id=AWS_KEY,
                            aws_secret_access_key=AWS_SECRET,
                            region_name=REGION)
client = boto3.client('dynamodb', aws_access_key_id=AWS_KEY,
                            aws_secret_access_key=AWS_SECRET,
                            region_name=REGION)

table = dynamodb.Table('customers')

#Describe table
response = client.describe_table(TableName='customers')
print (response)

#Scan table
response=table.scan()
items = response['Items']
for item in items:
    print (item)

#Scan table with filter
response = table.scan(FilterExpression=Attr('country').eq('India'))
items = response['Items']
for item in items:
    print (item)

#Scan table with filters
response = table.scan(
	FilterExpression=Attr('createdAt').between('2012-03-26T00:00:00-00:00',
					'2013-03-26T00:00:00-00:00'))
items = response['Items']
for item in items:
    print (item)

#Query table with partition key
response = table.query(
	KeyConditionExpression=Key('customerID').eq('1623072020799'))
items = response['Items']
for item in items:
    print (item)