import boto3
import csv

AWS_KEY="<enter>"
AWS_SECRET="<enter>"
REGION="us-east-2"

dynamodb = boto3.resource('dynamodb', aws_access_key_id=AWS_KEY,
                            aws_secret_access_key=AWS_SECRET,
                            region_name=REGION)
table = dynamodb.Table('customers')

reader = csv.reader(open("customers.csv","r"))
header=reader.next()

for row in reader:
    print (row)
    item = table.put_item(
        Item={
        	"customerID":row[0],
        	"name":row[1],
        	"address": row[2],
        	"city": row[3],
        	"zip": row[4],
        	"country": row[5],
        	"createdAt": row[6]
         })