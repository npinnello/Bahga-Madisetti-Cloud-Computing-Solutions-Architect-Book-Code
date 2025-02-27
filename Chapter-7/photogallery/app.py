
'''
MIT License

Copyright (c) 2019 Arshdeep Bahga and Vijay Madisetti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for, render_template, redirect, Response
from urllib.parse import quote
import os
import time
import datetime
import exifread
import json
import boto3
import pymysql
import requests
from boto3.dynamodb.conditions import Attr
pymysql.install_as_MySQLdb()
import MySQLdb
app = Flask(__name__, static_url_path="")

UPLOAD_FOLDER = os.path.join(app.root_path,'media')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
AWS_ACCESS_KEY="AKIATNVEVPSK6OCSSZSX"
AWS_SECRET_KEY="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"
REGION="us-east-2"
BUCKET_NAME="team9-photostorage-bucket-project2"

DB_HOSTNAME="team-9-rds.czawg22s2orh.us-east-2.rds.amazonaws.com"
DB_USERNAME = 'admin'
DB_PASSWORD = 't3am9masterpsswd'
DB_NAME = 'team_9_rds'

dynamodb = boto3.resource('dynamodb', aws_access_key_id=AWS_ACCESS_KEY,
                            aws_secret_access_key=AWS_SECRET_KEY,
                            region_name=REGION)

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
    print(path_filename)
    s3.upload_file(filenameWithPath, bucket, path_filename)
    s3.put_object_acl(ACL='public-read',
                Bucket=bucket, Key=path_filename)
    return "http://"+BUCKET_NAME+\
        ".s3-website-us-east-1.amazonaws.com/"+ path_filename

@app.route('/', methods=['GET', 'POST'])
def login():
    # Hardcoded credentials for testing
    HARDCODED_USERNAME = "Se422"
    HARDCODED_PASSWORD = "aws123"

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == HARDCODED_USERNAME and password == HARDCODED_PASSWORD:
            # Successful login
            conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM photo_gallery.team9-photostorage-bucket-project2;")
            results = cursor.fetchall()

            items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5]} for item in results]

            conn.close()
            print(items)
            return render_template('home.html', photos=items)
        else:
            # Invalid credentials
            return render_template('index.html', error="Invalid username or password")
    else:
        # Render login page for GET requests
        return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
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

        print(title,tags,description)
        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER,
                                        filename)
            print(filenameWithPath)
            file.save(filenameWithPath)
            uploadedFileURL = s3uploading(filename,
                                        filenameWithPath);
            ExifData=getExifData(filenameWithPath)
            ts=time.time()
            timestamp = datetime.datetime.\
                        fromtimestamp(ts).\
                        strftime('%Y-%m-%d %H:%M:%S')

            table.put_item(
            Item={
                    "PhotoID": str(int(ts*1000)),
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
    response = table.scan(
        FilterExpression=Attr('PhotoID').eq(str(photoID))
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

@app.route('/download/<path:image_name>')
def download_image(image_name):
        image_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/photos/{image_name}"

        response = requests.get(image_url, stream = True)

        # Sucess
        if response.status_code == 200:
                def generate():
                        for chunk in response.iter_content(chunk_size = 4096):
                                yield chunk
                encoded_filename = quote(image_name)

                return Response(generate(), headers = {
                        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                        "Content-Type": response.headers['Content-Type']
                })
        else:
                return "Error failed to download", response.status_code

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
