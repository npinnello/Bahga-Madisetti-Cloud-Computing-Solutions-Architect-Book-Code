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
DB_CONNECTION_NAME = "coms4220final:us-central1:photo-gallery-db"


# Sections & Categories
SECTIONS = {
    "ForSale": ["Boat", "Car", "Motorcycle", "Book", "Furniture"],
    "Housing": ["House", "Condo", "Apartment", "Townhouse", "Studio"],
    "Services": ["Plumbing", "Tutoring", "Handyman", "Landscaping", "Snow Removal"],
    "Jobs": ["Full-Time", "Part-Time", "Internship", "Co-op", "Seasonal"],
    "Community": ["Workshop", "Festival", "Cleanup", "Fundraiser", "Children"]
}

# Context processor to make sections available in all templates
@app.context_processor
def inject_sections():
    return dict(sections=SECTIONS)

# DB connection
def get_db_connection():
    try:
        return pymysql.connect(
            host='10.19.0.3',  # Your private IP from `gcloud sql instances list`
            user='root',
            password='se422',
            db='photo_gallery',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"MySQL connection error: {e}")
        raise



#Temp function for db connection testing
@app.route('/db-debug')
def db_debug():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        conn.close()
        return f"""
            <h1>Database Connection Successful</h1>
            <p>MySQL Version: {version['VERSION()']}</p>
            <p>Tables in {DB_NAME}:</p>
            <ul>
                {"".join(f"<li>{table['Tables_in_photo_gallery']}</li>" for table in tables)}
            </ul>
        """
    except Exception as e:
        return f"""
            <h1>Database Connection Failed</h1>
            <p style="color:red">Error: {str(e)}</p>
            <p>Attempted connection as: {DB_USER} to {DB_NAME}</p>
        """, 500

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
                session['user_id'] = user['user_id']  # Store user_id instead of username
                session['username'] = user['username']
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM listings")
                results = cursor.fetchall()
                conn.close()
                return render_template('home.html', listings=results)

            return render_template('index.html', error="Invalid username or password")
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
    if section not in SECTIONS or category not in SECTIONS[section]:
        abort(404)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        
        # Base query for all sections
        query = f"""
            SELECT 
                ID as id,
                Type as category,
                Description as description,
                Price as price,
                City as city,
                PhoneNumber as phone
        """
        
        # Section-specific fields with proper escaping
        if section == "ForSale":
            query += """,
                YearBuilt as year_built,
                MakeModel as make_model,
                Color as color,
                SubType as item_type,
                `ItemCondition` as `condition`
            """
        elif section == "Housing":
            query += """,
                YearBuilt as year_built,
                Bedrooms as bedrooms,
                Bathrooms as bathrooms,
                SquareFeet as square_feet,
                LotSize as lot_size
            """
        elif section == "Services":
            query += """,
                YearStarted as year_started,
                Availability as availability,
                ExperienceYears as experience_years
            """
        elif section == "Jobs":
            query += """,
                Title as title,
                Availability as availability,
                ExperienceYears as experience_years
            """
        elif section == "Community":
            query += """,
                Title as title,
                Date as date,
                Location as location,
                Organizer as organizer,
                ContactInfo as phone
            """

            
        query += f" FROM `{section}` WHERE Type=%s"
        
        cursor.execute(query, (category,))
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
        print(f"Database error in view_category: {e}")
        abort(500, description=str(e))

@app.route('/<section>/<category>/<int:item_id>')
def view_item(section, category, item_id):
    """Display single listing details"""
    if section not in SECTIONS or category not in SECTIONS[section]:
        abort(404)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Base SELECT
        query = f"""
            SELECT 
                ID as id,
                Type as category,
                Description as description,
                Price as price,
                City as city,
                PhoneNumber as phone
        """

        # Add section-specific fields
        if section == "ForSale":
            query += """,
                YearBuilt as year_built,
                MakeModel as make_model,
                Color as color,
                SubType as item_type,
                `ItemCondition` as `condition`
            """
        elif section == "Housing":
            query += """,
                YearBuilt as year_built,
                Bedrooms as bedrooms,
                Bathrooms as bathrooms,
                SquareFeet as square_feet,
                LotSize as lot_size
            """
        elif section == "Services":
            query += """,
                YearStarted as year_started,
                Availability as availability,
                ExperienceYears as experience_years
            """
        elif section == "Jobs":
            query += """,
                Title as title,
                Availability as availability,
                ExperienceYears as experience_years
            """
        elif section == "Community":
            query += """,
                Title as title,
                Date as date,
                Location as location,
                Organizer as organizer,
                ContactInfo as phone
            """

        query += f" FROM `{section}` WHERE id=%s AND Type=%s"

        cursor.execute(query, (item_id, category))
        item = cursor.fetchone()
        conn.close()

        if not item:
            abort(404)

        # Ensure 'title' is present for template
        if 'title' not in item or not item['title']:
            item['title'] = item.get('make_model') or item.get('description') or 'Listing'

        return render_template('item.html',
                               item=item,
                               section=section,
                               category=category)
    except pymysql.Error as e:
        print(f"Database error in view_item: {e}")
        abort(500)


@app.route('/create-listing/<section>/<category>', methods=['GET', 'POST'])
def create_listing(section, category):
    """Handle listing creation for all sections"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Convert URL parameter to match SECTIONS keys (capitalized, no hyphens)
    section_key = section.title().replace('-', '')
    
    if section_key not in SECTIONS or category not in SECTIONS[section_key]:
        abort(404)
    
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # The table name exactly matches the section key
            table_name = section_key
            
            # Common fields for all listings
            common_fields = {
                'Type': category,
                'Description': request.form['description'],
                'Price': request.form['price'],
                'City': request.form['city'],
                'PhoneNumber': request.form['phone']
            }
            
            # Section-specific fields
            extra_fields = {}
            if section_key == 'ForSale':
                extra_fields = {
                    'YearBuilt': request.form.get('year_built'),
                    'MakeModel': request.form.get('make_model'),
                    'Color': request.form.get('color'),
                    'SubType': request.form.get('item_type'),
                    'ItemCondition': request.form.get('condition')
                }
            elif section_key == 'Housing':
                extra_fields = {
                    'YearBuilt': request.form.get('year_built'),
                    'Bedrooms': request.form.get('bedrooms'),
                    'Bathrooms': request.form.get('bathrooms'),
                    'SquareFeet': request.form.get('square_feet'),
                    'LotSize': request.form.get('lot_size')
                }
            elif section_key == 'Services':
                extra_fields = {
                    'YearStarted': request.form.get('year_started'),
                    'Availability': request.form.get('availability'),
                    'ExperienceYears': request.form.get('experience_years')
                }
            elif section_key == 'Jobs':
                extra_fields = {
                    'Title': request.form.get('title'),
                    'Availability': request.form.get('availability'),
                    'ExperienceYears': request.form.get('experience_years')
                }
            elif section_key == 'Community':
                extra_fields = {
                    'Title': request.form.get('title'),
                    'Date': request.form.get('date'),
                    'Location': request.form.get('location'),
                    'Organizer': request.form.get('organizer')
                }
            
            # Combine all fields
            all_fields = {**common_fields, **extra_fields}
            
            # Build the SQL query
            columns = ', '.join(all_fields.keys())
            placeholders = ', '.join(['%s'] * len(all_fields))
            values = list(all_fields.values())
            
            cursor.execute(
                f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})",
                values
            )
            conn.commit()
            conn.close()
            
            flash("Listing created successfully!", "success")
            return redirect(url_for('view_category', section=section, category=category))
            
        except pymysql.Error as e:
            print(f"Database error: {e}")
            flash("Database error occurred", "danger")
    
    # For GET request, show the form
    return render_template('create_listing.html',
                         section=section,
                         category=category,
                         section_key=section_key)

@app.route('/health')
def health():
    return "OK", 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
