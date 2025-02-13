#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask import render_template, redirect
import os
import time
import datetime
import exifread
import json
import boto3
import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb

app = Flask(__name__, static_url_path="")

UPLOAD_FOLDER = os.path.join(app.root_path,'static','media')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

BASE_URL="http://localhost:5000/media/"

# ✅ Corrected AWS Region
REGION="us-east-2"

# ✅ AWS Credentials are now loaded from environment variables (Set these on EC2)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

# ✅ Use your correct S3 bucket name
BUCKET_NAME="photogallery-bucket-422"

# ✅ RDS Configuration (Make sure to use your correct DB credentials)
DB_HOSTNAME="team-9-rds.czawg22s2orh.us-east-2.rds.amazonaws.com"
DB_USERNAME = 'admin'
DB_PASSWORD = 't3am9masterpsswd'
DB_NAME = 'team-9-rds'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

def getExifData(path_name):
    with open(path_name, 'rb') as f:
        tags = exifread.process_file(f)
    ExifData = {tag: str(tags[tag]) for tag in tags.keys() if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote')}
    return ExifData

# ✅ Fixed S3 Upload URL
def s3uploading(filename, filenameWithPath):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    bucket = BUCKET_NAME
    path_filename = "photos/" + filename
    print(path_filename)

    s3.upload_file(filenameWithPath, bucket, path_filename)
    s3.put_object_acl(ACL='public-read', Bucket=bucket, Key=path_filename)

    return f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{path_filename}"

@app.route('/', methods=['GET'])
def home_page():
    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM photogallerydb.photogallery2;")
    results = cursor.fetchall()

    items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5]} for item in results]

    conn.close()
    print(items)
    return render_template('index.html', photos=items)

@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':
        uploadedFileURL = ''
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        print(title, tags, description)

        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER, filename)
            print(filenameWithPath)
            file.save(filenameWithPath)
            uploadedFileURL = s3uploading(filename, filenameWithPath)
            ExifData = getExifData(filenameWithPath)
            print(ExifData)

            ts = time.time()
            timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
            cursor = conn.cursor()

            # ✅ Fixed SQL Injection Risk (Parameterized Query)
            statement = """INSERT INTO photogallerydb.photogallery2 
                           (CreationTime, Title, Description, Tags, URL, EXIF) 
                           VALUES (%s, %s, %s, %s, %s, %s);"""
            cursor.execute(statement, (timestamp, title, description, tags, uploadedFileURL, json.dumps(ExifData)))

            conn.commit()
            conn.close()

        return redirect('/')
    else:
        return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM photogallerydb.photogallery2 WHERE PhotoID=%s;", (photoID,))
    results = cursor.fetchall()

    items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5], "ExifData": json.loads(item[6])} for item in results]

    conn.close()
    tags = items[0]['Tags'].split(',')
    exifdata = items[0]['ExifData']

    return render_template('photodetail.html', photo=items[0], tags=tags, exifdata=exifdata)

@app.route('/search', methods=['GET'])
def search_page():
    query = request.args.get('query', None)

    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM photogallerydb.photogallery2 WHERE Title LIKE %s
        UNION 
        SELECT * FROM photogallerydb.photogallery2 WHERE Description LIKE %s
        UNION 
        SELECT * FROM photogallerydb.photogallery2 WHERE Tags LIKE %s;
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))

    results = cursor.fetchall()

    items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5], "ExifData": item[6]} for item in results]

    conn.close()
    print(items)
    return render_template('search.html', photos=items, searchquery=query)

# ✅ Run Flask on Port 80 for AWS EC2
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)