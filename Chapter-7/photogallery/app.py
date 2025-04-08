#!/usr/bin/env python3
from flask import Flask, jsonify, abort, request, make_response, url_for, render_template, redirect, Response, send_from_directory
from urllib.parse import quote
# from google.cloud import storage
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

UPLOAD_FOLDER = os.path.join(app.root_path, 'media')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Google Cloud SQL configuration
DB_USER = "root"
DB_PASSWORD = "se422"
DB_NAME = "photo_gallery"
DB_CONNECTION_NAME = "se422proj4:us-central1:photo-gallery-db"
DB_HOST = "34.58.7.121"

# GCS Configuration
BUCKET_NAME = os.getenv("BUCKET_NAME", "se-422-photo-gallery")

def get_db_connection():
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=3306,
            user=DB_USER,
            password=DB_PASSWORD,
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

def getExifData(file_stream):
    tags = exifread.process_file(file_stream)
    return {tag: str(tags[tag]) for tag in tags if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote')}

def upload_to_gcs(file):
    if not BUCKET_NAME:
        raise ValueError("BUCKET_NAME environment variable not set")

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    filename = secure_filename(file.filename)
    blob = bucket.blob(f"photos/{filename}")
    blob.upload_from_file(file, content_type=file.content_type)
    return f"https://storage.googleapis.com/{BUCKET_NAME}/photos/{filename}"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            conn.close()

            if user and user['password'] == password:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM photos")
                results = cursor.fetchall()
                for photo in results:
                    photo['URL'] = photo['storage_path']  # Alias for template compatibility
                conn.close()

                return render_template('home.html', photos=results)

            return render_template('index.html', error="Invalid username or password")
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('index.html', error="Database error occurred. Please try again.")
    return render_template('index.html')

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('create-user.html', error="Username and password are required")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return render_template('create-user.html', error="Username already exists")

            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            conn.close()
            return render_template('index.html', message="User created successfully. Please log in.")
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('create-user.html', error="Database error occurred. Please try again.")
    return render_template('create-user.html')

@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        if file and allowed_file(file.filename):
            public_url = upload_to_gcs(file)
            file.stream.seek(0)
            ExifData = getExifData(file.stream)
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT album_id FROM albums WHERE user_id = %s LIMIT 1", (1,))
                album = cursor.fetchone()

                if not album:
                    cursor.execute("INSERT INTO albums (user_id, title, description, created_at) VALUES (%s, %s, %s, %s)",
                                   (1, 'Default Album', 'Auto-created album', timestamp))
                    conn.commit()
                    cursor.execute("SELECT LAST_INSERT_ID() AS album_id")
                    album = cursor.fetchone()

                cursor.execute("INSERT INTO photos (album_id, user_id, title, description, storage_path, upload_date) VALUES (%s, %s, %s, %s, %s, %s)",
                               (album['album_id'], 1, title, description, public_url, timestamp))
                conn.commit()
                conn.close()
                return redirect('/')
            except pymysql.Error as e:
                print(f"Photo insert failed: {e}")
                return render_template('form.html', error="Failed to add photo.")
    return render_template('form.html')

@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos WHERE photo_id = %s", (photoID,))
    item = cursor.fetchone()
    conn.close()

    if item:
        item['URL'] = item['storage_path']  # Alias for templates
        tags = []
        exifdata = {}
        return render_template('photodetail.html', photo=item, tags=tags, exifdata=exifdata)
    else:
        abort(404)
        
@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory('media', filename)

@app.route('/search', methods=['GET'])
def search_page():
    query = request.args.get('query', None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos WHERE title LIKE %s OR description LIKE %s", 
                   (f"%{query}%", f"%{query}%"))
    items = cursor.fetchall()
    for item in items:
        item['URL'] = item['storage_path']  # Alias for template
    conn.close()
    return render_template('search.html', photos=items, searchquery=query)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve a file from the local UPLOAD_FOLDER."""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
