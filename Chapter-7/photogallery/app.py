from flask import Flask, render_template, request, redirect, session, url_for, jsonify, abort
import pymysql
import os
from datetime import datetime

app = Flask(__name__)

# Google Cloud SQL configuration
DB_USER = "root"
DB_PASSWORD = "se422"
DB_NAME = "photo_gallery"
DB_CONNECTION_NAME = "se422proj4:us-central1:photo-gallery-db"


# Sections & Categories
SECTIONS = {
    "for-sale": ["cars-trucks", "motorcycles", "boats", "books", "furniture"],
    "housing": ["apartments", "rooms", "sublets", "parking", "storage"],
    "services": ["cleaning", "tutoring", "plumbing", "beauty", "moving"],
    "jobs": ["tech", "retail", "education", "hospitality", "freelance"],
    "community": ["events", "volunteers", "activities", "classes", "lost-found"]
}

# DB connection

def get_db_connection():
    try:
        unix_socket = f"/cloudsql/{DB_CONNECTION_NAME}"
        return pymysql.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            unix_socket=unix_socket,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"MySQL connection error: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html', sections=SECTIONS)

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
                 # CHANGE ONCE FINAL
                cursor.execute("SELECT * FROM listings")  
                results = cursor.fetchall()
                conn.close()

                return render_template('home.html', listings=results)

            return render_template('index.html', error="Invalid username or password")
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('index.html', error="Database error occurred. Please try again.")
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/<section>')
def view_section(section):
    if section not in SECTIONS:
        abort(404)
    return render_template('section.html', section=section, categories=SECTIONS[section])

@app.route('/<section>/<category>')
def view_category(section, category):
    conn = get_db_connection()
    cursor = conn.cursor()
    # CHANGE ONCE FINAL
    cursor.execute("SELECT * FROM listings WHERE section=%s AND category=%s", (section, category))
    items = cursor.fetchall()
    conn.close()
    return render_template('category.html', section=section, category=category, items=items)

@app.route('/<section>/<category>/<int:item_id>')
def view_item(section, category, item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # CHANGE ONCE FINAL
    cursor.execute("SELECT * FROM listings WHERE listing_id=%s", (item_id,))
    item = cursor.fetchone()
    conn.close()
    if not item:
        abort(404)
    return render_template('item.html', item=item)

@app.route('/create-listing/<section>/<category>', methods=['GET', 'POST'])
def create_listing(section, category):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # CHANGE ONCE FINAL
    if request.method == 'POST':
        form = request.form
                attributes = (
            session['user_id'], section, category,
            form['title'], form['description'],
            form['year'], form['make'], form['color'],
            form['item_type'], form['condition'],
            form['price'], form['city'], form['phone'],
            datetime.utcnow()
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        # CHANGE ONCE FINAL
        cursor.execute("""
            INSERT INTO listings
            (user_id, section, category, title, description, year_built, make_model,
             color, item_type, item_condition, price, city, phone, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, attributes)
        conn.commit()
        conn.close()

        return redirect(url_for('view_category', section=section, category=category))

    return render_template('create_listing.html', section=section, category=category)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
