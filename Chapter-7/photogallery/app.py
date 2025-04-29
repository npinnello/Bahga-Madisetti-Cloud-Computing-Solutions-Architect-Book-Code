from flask import Flask, render_template, request, redirect, session, url_for, jsonify, abort
import pymysql
import os
from datetime import datetime

# Initialize Flask app with explicit template folder
app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-secret-key-here'  # Required for session management
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates during development

# Database configuration
DB_CONFIG = {
    'host': 'localhost',  # Default for local development
    'user': "root",
    'password': "se422",
    'database': "photo_gallery",
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Application sections and categories
SECTIONS = {
    "for-sale": ["cars-trucks", "motorcycles", "boats", "books", "furniture"],
    "housing": ["apartments", "rooms", "sublets", "parking", "storage"],
    "services": ["cleaning", "tutoring", "plumbing", "beauty", "moving"],
    "jobs": ["tech", "retail", "education", "hospitality", "freelance"],
    "community": ["events", "volunteers", "activities", "classes", "lost-found"]
}

def get_db_connection():
    try:
        return pymysql.connect(
            host='localhost',
            user='root',
            password='se422',
            database='photo_gallery',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"MySQL connection error: {e}")
        raise

@app.route('/')
def index():
    return render_template('classifieds/index.html', sections=SECTIONS)

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, username, password FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()
                
        if user and user['password'] == password:
            session['user_id'] = user['user_id']
            return redirect(url_for('home'))
        return render_template('classifieds/index.html', 
                            sections=SECTIONS,
                            error="Invalid username or password")
    except pymysql.Error as e:
        print(f"Database error: {e}")
        return render_template('classifieds/index.html',
                            sections=SECTIONS,
                            error="Database error occurred")

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('classifieds/home.html', sections=SECTIONS)

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    """User registration endpoint"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('classifieds/create-user.html',
                                error="Username and password are required")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM users WHERE username = %s",
                        (username,)
                    )
                    if cursor.fetchone():
                        return render_template('classifieds/create-user.html',
                                            error="Username already exists")

                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, password)
                    )
                    conn.commit()
            
            return render_template('classifieds/index.html',
                                sections=SECTIONS,
                                message="User created successfully. Please log in.")
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('classifieds/create-user.html',
                                error="Database error occurred")

    return render_template('classifieds/create-user.html')

@app.route('/logout')
def logout():
    """Clear user session"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/<section>')
def view_section(section):
    """Display all categories in a section"""
    if section not in SECTIONS:
        abort(404)
    return render_template('classifieds/section.html',
                         section=section,
                         categories=SECTIONS[section])

@app.route('/<section>/<category>')
def view_category(section, category):
    """Show listings for a specific category"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM listings WHERE section=%s AND category=%s",
                    (section, category)
                )
                items = cursor.fetchall()
        
        if not items:
            flash("No listings found in this category", "info")
            return redirect(url_for('view_section', section=section))
            
        return render_template('classifieds/category.html',
                            section=section,
                            category=category,
                            items=items)
    except pymysql.Error as e:
        app.logger.error(f"Database error in view_category: {e}")
        abort(500)

@app.route('/<section>/<category>/<int:item_id>')
def view_item(section, category, item_id):
    """Display single listing details"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM listings WHERE listing_id=%s",
                    (item_id,)
                )
                item = cursor.fetchone()
        
        if not item or item['section'] != section or item['category'] != category:
            abort(404)
            
        return render_template('classifieds/item.html', item=item)
    except pymysql.Error as e:
        print(f"Database error: {e}")
        abort(500)

@app.route('/create-listing/<section>/<category>', methods=['GET', 'POST'])
def create_listing(section, category):
    """Handle new listing creation"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if section not in SECTIONS or category not in SECTIONS[section]:
        abort(404)
    
    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO listings 
                        (user_id, section, category, title, description, 
                         year_built, make_model, color, item_type, 
                         item_condition, price, city, phone, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session['user_id'], section, category,
                        request.form['title'], request.form['description'],
                        request.form.get('year_built'), request.form.get('make_model'),
                        request.form.get('color'), request.form.get('item_type'),
                        request.form.get('condition'), request.form['price'],
                        request.form['city'], request.form['phone'],
                        datetime.utcnow()
                    ))
                    conn.commit()
            
            return redirect(url_for('view_category',
                                 section=section,
                                 category=category))
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return render_template('classifieds/create_listing.html',
                                section=section,
                                category=category,
                                error="Database error occurred")
    
    return render_template('classifieds/create_listing.html',
                         section=section,
                         category=category)

@app.errorhandler(500)
def server_error(error):
    """500 error handler"""
    return render_template('classifieds/500.html'), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('classifieds/404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)