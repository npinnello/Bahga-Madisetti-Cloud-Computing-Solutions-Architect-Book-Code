#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for, render_template, redirect, Response
from urllib.parse import quote
from google.cloud import storage
from werkzeug.utils import secure_filename
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
DB_USER = "root"
DB_PASSWORD = "se422"
DB_NAME = "photo_gallery"
DB_CONNECTION_NAME = "se4220hw3:us-central1:photo-gallery-db"

# Function to establish connection with Google Cloud SQL
def get_db_connection():
    try:
        # For local development with Cloud SQL Proxy
        return pymysql.connect(
            host='34.41.49.24',
            port=3306,
            user=DB_USER,
            password=DB_PASSWORD,  # Make sure this is set
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise

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

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get user by username
            cursor.execute("""
                SELECT user_id, username, password 
                FROM users 
                WHERE username = %s
            """, (username,))
            
            user = cursor.fetchone()
            conn.close()

            # Simple password comparison
            if user and user['password'] == password:
                
                # Get photos for the gallery
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM photos")
                results = cursor.fetchall()
                conn.close()

                # Prepare photo data for template
                photos = [{
                    "PhotoID": item[0],
                    "CreationTime": item[1],
                    "Title": item[2], 
                    "Description": item[3],
                    "Tags": item[4],
                    "URL": item[5]
                } for item in results]
                
                return render_template('home.html', photos=photos)
            
            return render_template('index.html', 
                                error="Invalid username or password")
        
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('index.html', 
                                error="Database error occurred. Please try again.")
    
    return render_template('index.html')


@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Basic validation
        if not username or not password:
            return render_template('create-user.html', 
                                error="Username and password are required")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if username exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return render_template('create-user.html', 
                                    error="Username already exists")
            
            # Insert new user (plain password storage - not recommended for production)
            cursor.execute("""
                INSERT INTO users (username, password)
                VALUES (%s, %s)
            """, (username, password))
            
            conn.commit()
            conn.close()
            return render_template('index.html', 
                                message="User created successfully. Please log in.")
        
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('create-user.html', 
                                error="Database error occurred. Please try again.")
    
    return render_template('create-user.html')


# @app.route('/add', methods=['GET', 'POST'])
# def add_photo():
#     if request.method == 'POST':
#         file = request.files['imagefile']
#         title = request.form['title']
#         tags = request.form['tags']
#         description = request.form['description']

#         if file and allowed_file(file.filename):
#             filename = file.filename
#             filenameWithPath = os.path.join(UPLOAD_FOLDER, filename)
#             file.save(filenameWithPath)
#             ExifData = getExifData(filenameWithPath)
#             ts = time.time()
#             timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

#             conn = get_db_connection()
#             cursor = conn.cursor()
#             cursor.execute(
#                 "INSERT INTO photo (CreationTime, Title, Description, Tags, URL, ExifData) VALUES (%s, %s, %s, %s, %s, %s)",
#                 (timestamp, title, description, tags, "GCS_URL", json.dumps(ExifData))
#             )
#             conn.commit()
#             conn.close()
#         return redirect('/')
#     else:
#         return render_template('form.html')

def upload_to_gcs(file):
    """Uploads a file to Google Cloud Storage"""
    if not file or not allowed_file(file.filename):
        return None
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(os.getenv("BUCKET_NAME"))
    
    # Secure filename & upload
    filename = secure_filename(file.filename)
    blob = bucket.blob(f"photos/{filename}")
    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )
    blob.make_public()
    return blob.public_url

@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        if file and allowed_file(file.filename):
            # Upload to Cloud Storage
            public_url = upload_to_gcs(file)
            if not public_url:
                abort(400, "Invalid file type")

            # Save to Cloud SQL
            ts = time.time()
            timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            ExifData = getExifData(file.stream)  # Modify to read from file object

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO photos (CreationTime, Title, Description, Tags, URL, ExifData) VALUES (%s, %s, %s, %s, %s, %s)",
                (timestamp, title, description, tags, public_url, json.dumps(ExifData)))
            conn.commit()
            conn.close()
            return redirect('/')
    return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos WHERE PhotoID = %s", (photoID,))
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
    cursor.execute("SELECT * FROM photos WHERE Title LIKE %s OR Description LIKE %s OR Tags LIKE %s", (f'%{query}%', f'%{query}%', f'%{query}%'))
    items = cursor.fetchall()
    conn.close()
    return render_template('search.html', photos=items, searchquery=query)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
