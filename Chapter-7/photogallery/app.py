from flask import Flask, render_template, request, redirect, session, url_for, abort
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
                session['username'] = user['username']
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM listings")  # CHANGE ONCE FINAL
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
    # TODO: Replace with dynamic table selection based on section (e.g., ForSale, Housing)
    cursor.execute("SELECT * FROM ForSale WHERE Type=%s", (category,))
    items = cursor.fetchall()
    conn.close()
    return render_template('category.html', section=section, category=category, items=items)

@app.route('/<section>/<category>/<int:item_id>')
def view_item(section, category, item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # TODO: Replace with dynamic lookup based on section table
    cursor.execute("SELECT * FROM ForSale WHERE ID=%s", (item_id,))
    item = cursor.fetchone()
    conn.close()
    if not item:
        abort(404)
    return render_template('item.html', item=item)

@app.route('/create-listing/<section>/<category>', methods=['GET', 'POST'])
def create_listing(section, category):
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        form = request.form
        attributes = (
            category,
            form['title'], form['description'],
            form['year'], form['make'], form['color'],
            form['item_type'], form['condition'],
            form['price'], form['city'], form['phone'],
            datetime.utcnow()
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        # TODO: Adjust INSERT to use correct table like ForSale, Housing, etc.
        cursor.execute("""
            INSERT INTO ForSale
            (Type, Title, Description, YearBuilt, MakeModel,
             Color, SubType, ItemCondition, Price, City, PhoneNumber, CreatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, attributes)
        conn.commit()
        conn.close()

        return redirect(url_for('view_category', section=section, category=category))

    return render_template('create_listing.html', section=section, category=category)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
