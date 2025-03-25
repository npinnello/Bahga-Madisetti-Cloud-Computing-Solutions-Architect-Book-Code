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
import pymysql
import requests
pymysql.install_as_MySQLdb()
import MySQLdb
app = Flask(__name__, static_url_path="")

UPLOAD_FOLDER = os.path.join(app.root_path,'media')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Google Cloud SQL configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_CONNECTION_NAME = os.getenv("DB_CONNECTION_NAME")

# Function to establish connection with Google Cloud SQL
def get_db_connection():
    return pymysql.connect(
        unix_socket=f"/cloudsql/{DB_CONNECTION_NAME}",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME
    )

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

from werkzeug.security import check_password_hash
import MySQLdb

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user[2] == password :
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM photo;")
            results = cursor.fetchall()
            conn.close()

            items = [{"PhotoID": item[0], "CreationTime": item[1], "Title": item[2], "Description": item[3], "Tags": item[4], "URL": item[5]} for item in results]
            return render_template('home.html', photos=items)
        else:
            return render_template('index.html', error="Invalid username or password")

    else:
        return render_template('index.html')


@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            conn.close()
            return render_template('create-user.html', error="Username already exists.")
        
        cursor.execute("INSERT INTO user (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        conn.close()

        return render_template('index.html', message="User created successfully. Please log in.")

    return render_template('create-user.html')


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
            ExifData = getExifData(filenameWithPath)
            ts = time.time()
            timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO photo (CreationTime, Title, Description, Tags, URL, ExifData) VALUES (%s, %s, %s, %s, %s, %s)",
                (timestamp, title, description, tags, "GCS_URL", json.dumps(ExifData))
            )
            conn.commit()
            conn.close()
        return redirect('/')
    else:
        return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo WHERE PhotoID = %s", (photoID,))
    item = cursor.fetchone()
    conn.close()

    if item:
        tags = item[4].split(',')
        exifdata = json.loads(item[6])
        return render_template('photodetail.html', photo=item, tags=tags, exifdata=exifdata)
    else:
        abort(404)

@app.route('/search', methods=['GET'])
def search_page():
    query = request.args.get('query', None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo WHERE Title LIKE %s OR Description LIKE %s OR Tags LIKE %s", (f'%{query}%', f'%{query}%', f'%{query}%'))
    items = cursor.fetchall()
    conn.close()
    return render_template('search.html', photos=items, searchquery=query)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)