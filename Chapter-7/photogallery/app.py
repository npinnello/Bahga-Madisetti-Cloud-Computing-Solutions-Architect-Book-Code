#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask import render_template, redirect
import os
import boto3    
import time
import datetime
from boto3.dynamodb.conditions import Key, Attr
import exifread
import json

app = Flask(__name__, static_url_path="", static_folder="static", template_folder="templates")

UPLOAD_FOLDER = os.path.join(app.root_path,'media')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
AWS_ACCESS_KEY="AKIATNVEVPSKVP4QH2LN"
AWS_SECRET_KEY="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"
REGION="us-east-2"
BUCKET_NAME="team9-photostorage-bucket-project2"

dynamodb = boto3.resource('dynamodb', aws_access_key_id=AWS_ACCESS_KEY,
                            aws_secret_access_key=AWS_SECRET_KEY,
                            region_name=REGION)

# Updated table name to 'photo_gallery'
table = dynamodb.Table('photo_gallery')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

def getExifData(path_name):
    f = open(path_name, 'rb')
    tags = exifread.process_file(f)
    ExifData={}
    for tag in tags.keys():
        if tag not in ('JPEGThumbnail', 
                        'TIFFThumbnail', 
                        'Filename', 
                        'EXIF MakerNote'):            
            key="%s"%(tag)
            val="%s"%(tags[tag])
            ExifData[key]=val
    return ExifData

def s3uploading(filename, filenameWithPath):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY,
                            aws_secret_access_key=AWS_SECRET_KEY)
                       
    bucket = BUCKET_NAME
    path_filename = "photos/" + filename
    print (path_filename)
    s3.upload_file(filenameWithPath, bucket, path_filename)  
    s3.put_object_acl(ACL='public-read', 
                Bucket=bucket, Key=path_filename)
    return "http://"+BUCKET_NAME+\
        ".s3-website-us-east-1.amazonaws.com/"+ path_filename  

@app.route('/', methods=['GET', 'POST'])
def home_page():
    response = table.scan()

    items = response['Items']
    print(items)

    return render_template('index.html', photos=items)

@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':    
        uploadedFileURL=''

        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        print (title,tags,description)
        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER, 
                                        filename)
            print (filenameWithPath)
            file.save(filenameWithPath)
            uploadedFileURL = s3uploading(filename, 
                                        filenameWithPath);
            ExifData=getExifData(filenameWithPath)
            ts=time.time()
            timestamp = datetime.datetime.\
                        fromtimestamp(ts).\
                        strftime('%Y-%m-%d %H:%M:%S')

            # Updated partition key to 'photo_id'
            table.put_item(
            Item={
                    "photo_id": str(int(ts*1000)),  # Updated to 'photo_id'
                    "CreationTime": timestamp,
                    "Title": title,
                    "Description": description,
                    "Tags": tags,
                    "URL": uploadedFileURL,
                    "ExifData": json.dumps(ExifData)
                }
            )

        return redirect('/')
    else:
        return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    # Updated partition key to 'photo_id'
    response = table.scan(
        FilterExpression=Attr('photo_id').eq(str(photoID))  # Updated to 'photo_id'
    )

    items = response['Items']
    print(items[0])
    tags=items[0]['Tags'].split(',')
    exifdata=json.loads(items[0]['ExifData'])

    return render_template('photodetail.html', 
            photo=items[0], tags=tags, exifdata=exifdata)

@app.route('/search', methods=['GET'])
def search_page():
    query = request.args.get('query', None)    
    
    response = table.scan(
        FilterExpression=Attr('Title').contains(str(query)) | 
                        Attr('Description').contains(str(query)) | 
                        Attr('Tags').contains(str(query))
    )
    items = response['Items']
    return render_template('search.html', 
            photos=items, searchquery=query)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)