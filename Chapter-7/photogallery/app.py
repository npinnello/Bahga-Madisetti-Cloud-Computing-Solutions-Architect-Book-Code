from flask import Flask, render_template, request, redirect, session, url_for, abort, flash
import pymysql
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

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

# Context processor to make sections available in all templates
@app.context_processor
def inject_sections():
    return dict(sections=SECTIONS)

# DB connection
def get_db_connection():
    try:
        if os.name == 'nt':  # Windows
            return pymysql.connect(
                host='localhost',
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        else:  # Unix/Linux (Google Cloud)
            return pymysql.connect(
                unix_socket=f"/cloudsql/{DB_CONNECTION_NAME}",
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
    except pymysql.MySQLError as e:
        print(f"MySQL connection error: {e}")
        raise

# Routes
@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html', sections=SECTIONS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login requests"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, password FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            conn.close()
            
            if user and user['password'] == password:
                session['user_id'] = user['user_id']
                return redirect(url_for('home'))
            flash("Invalid username or password", "danger")
        except pymysql.Error as e:
            print(f"Database error: {e}")
            flash("Database error occurred", "danger")
    
    return render_template('login.html')

@app.route('/home')
def home():
    """Main dashboard after login"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    """User registration endpoint"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Username and password are required", "danger")
            return redirect(url_for('create_user'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            if cursor.fetchone():
                flash("Username already exists", "danger")
                conn.close()
                return redirect(url_for('create_user'))

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
            conn.close()
            
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('index'))
        except pymysql.Error as e:
            print(f"Database error: {e}")
            flash("Database error occurred", "danger")
    
    return render_template('create_user.html')

@app.route('/<section>')
def view_section(section):
    """Display all categories in a section"""
    if section not in SECTIONS:
        abort(404)
    return render_template('section.html', 
                         section=section,
                         categories=SECTIONS[section])

@app.route('/<section>/<category>')
def view_category(section, category):
    """Show listings for a specific category"""
    if section not in SECTIONS or category not in SECTIONS[section]:
        abort(404)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Dynamic table selection based on section
        table_name = section.replace('-', '')
        cursor.execute(f"""
            SELECT * FROM {table_name} 
            WHERE category=%s
        """, (category,))
        items = cursor.fetchall()
        conn.close()
        
        if not items:
            flash(f"No listings found in {category}", "info")
            return redirect(url_for('view_section', section=section))
            
        return render_template('category.html',
                            section=section,
                            category=category,
                            items=items)
    except pymysql.Error as e:
        print(f"Database error: {e}")
        abort(500)

@app.route('/<section>/<category>/<int:item_id>')
def view_item(section, category, item_id):
    """Display single listing details"""
    if section not in SECTIONS or category not in SECTIONS[section]:
        abort(404)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Dynamic table selection based on section
        table_name = section.replace('-', '')
        cursor.execute(f"""
            SELECT * FROM {table_name} 
            WHERE id=%s AND category=%s
        """, (item_id, category))
        item = cursor.fetchone()
        conn.close()
        
        if not item:
            abort(404)
            
        return render_template('item.html', 
                            item=item,
                            section=section,
                            category=category)
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
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Dynamic table selection based on section
            table_name = section.replace('-', '')
            cursor.execute(f"""
                INSERT INTO {table_name} 
                (user_id, category, title, description, 
                 year_built, make_model, color, item_type, 
                 condition, price, city, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'], category,
                request.form['title'], request.form['description'],
                request.form.get('year_built'), request.form.get('make_model'),
                request.form.get('color'), request.form.get('item_type'),
                request.form.get('condition'), request.form['price'],
                request.form['city'], request.form['phone'],
                datetime.utcnow()
            ))
            conn.commit()
            conn.close()
            
            flash("Listing created successfully!", "success")
            return redirect(url_for('view_category',
                                 section=section,
                                 category=category))
        except pymysql.Error as e:
            print(f"Database error: {e}")
            flash("Database error occurred", "danger")
    
    return render_template('create_listing.html',
                         section=section,
                         category=category)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)