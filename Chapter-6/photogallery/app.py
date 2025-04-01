# !/usr/bin/env python3
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

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'media')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
BASE_URL = "http://localhost:5000/media/"
REGION = "us-east-2"

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
BUCKET_NAME = "team-9-photostorage-bucket"

DB_HOSTNAME = "team-9-rds.czawg22s2orh.us-east-2.rds.amazonaws.com"
DB_USERNAME = 'admin'
DB_PASSWORD = 't3am9masterpsswd'
DB_NAME = 'team_9_rds'

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
    return {tag: str(tags[tag]) for tag in tags if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote')}

def s3uploading(filename, filenameWithPath):
    bucket_name = os.getenv("BUCKET_NAME", "se-422-photo-gallery")  # fallback or override as needed

    if not bucket_name:
        raise ValueError("Cannot determine path without bucket name")

    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    path_filename = "photos/" + filename
    s3.upload_file(filenameWithPath, bucket_name, path_filename)

    return f"https://{bucket_name}.s3.{REGION}.amazonaws.com/{path_filename}"


@app.route('/', methods=['GET'])
def home_page():
    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos;")
    results = cursor.fetchall()
    conn.close()
    items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5]} for item in results]
    return render_template('index.html', photos=items)

@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filenameWithPath)
            uploadedFileURL = s3uploading(filename, filenameWithPath)
            ExifData = getExifData(filenameWithPath)
            timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

            conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
            cursor = conn.cursor()
            statement = """INSERT INTO photos 
                           (CreationTime, Title, Description, Tags, URL, ExifData) 
                           VALUES (%s, %s, %s, %s, %s, %s);"""
            cursor.execute(statement, (timestamp, title, description, tags, uploadedFileURL, json.dumps(ExifData)))
            conn.commit()
            conn.close()
        return redirect('/')
    return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos WHERE PhotoID=%s;", (photoID,))
    item = cursor.fetchone()
    conn.close()

    if item:
        tags = item[4].split(',')
        exifdata = json.loads(item[6])
        photo = {
            "PhotoID": item[0], "CreationTime": item[1], "Title": item[2],
            "Description": item[3], "Tags": item[4], "URL": item[5], "ExifData": exifdata
        }
        return render_template('photodetail.html', photo=photo, tags=tags, exifdata=exifdata)
    else:
        abort(404)

@app.route('/search', methods=['GET'])
def search_page():
    query = request.args.get('query', '')
    conn = MySQLdb.connect(host=DB_HOSTNAME, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, port=3306)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM photos 
        WHERE Title LIKE %s OR Description LIKE %s OR Tags LIKE %s;
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))
    results = cursor.fetchall()
    conn.close()

    items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5], "ExifData": item[6]} for item in results]
    return render_template('search.html', photos=items, searchquery=query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
