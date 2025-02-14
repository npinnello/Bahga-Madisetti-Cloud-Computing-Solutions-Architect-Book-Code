import MySQLdb


DB_USERNAME = 'admin'  # Must match the RDS username
DB_PASSWORD = 't3am9masterpsswd'  # Ensure this is correct
DB_NAME = 'team-9-rds'  # Use the exact database name
RDS_HOSTNAME = 'team-9-rds.czawg22s2orh.us-east-2.rds.amazonaws.com'


try:
    conn = MySQLdb.connect(
        host=RDS_HOSTNAME,
        user=DB_USERNAME,
        passwd=DB_PASSWORD,
        db=DB_NAME,
        port=3306
    )
    print("✅ Connected to MySQL RDS successfully!")

    cursor = conn.cursor()

 
    cursor.execute("SELECT VERSION();")
    version = cursor.fetchone()
    print(f"MySQL Server Version: {version[0]}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photogallery2 (
            PhotoID INT AUTO_INCREMENT PRIMARY KEY,
            CreationTime DATETIME NOT NULL,
            Title VARCHAR(255) NOT NULL,
            Description TEXT NOT NULL,
            Tags VARCHAR(255) NOT NULL,
            URL TEXT NOT NULL,
            EXIF TEXT NOT NULL
        );
    """)
    
    print("✅ Table `photogallery2` created (if not exists)")

    cursor.close()
    conn.close()
    print("✅ Database connection closed.")

except MySQLdb.OperationalError as e:
    print(f"❌ MySQL Connection Error: {e}")
except MySQLdb.Error as e:
    print(f"❌ MySQL Error: {e}")
