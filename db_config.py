import mysql.connector
from mysql.connector import Error
import os

class DatabaseConnection:
    def __init__(self):
        """Initialize database connection"""
        try:
            # Railway automatically creates MYSQLHOST, MYSQLUSER, etc. when MySQL service is added
            # Also check for MYSQL_URL or MYSQL_PUBLIC_URL which Railway might provide
            # Check for Railway's auto-generated variables first, then fall back to custom DB_* variables
            
            # Check if Railway provides a connection URL (parse it if available)
            mysql_url = os.getenv("MYSQL_URL") or os.getenv("MYSQL_PUBLIC_URL")
            if mysql_url:
                # Parse MySQL URL: mysql://user:password@host:port/database
                import urllib.parse
                parsed = urllib.parse.urlparse(mysql_url)
                db_host = parsed.hostname
                db_user = parsed.username or "root"
                db_password = parsed.password or ""
                db_name = parsed.path.lstrip('/') or "railway"
                db_port = parsed.port or 3306
            else:
                # Use individual environment variables
                db_host = os.getenv("MYSQLHOST") or os.getenv("DB_HOST", "localhost")
                db_user = os.getenv("MYSQLUSER") or os.getenv("DB_USER", "root")
                db_password = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or os.getenv("DB_PASSWORD", "1234")
                db_name = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME", "face_animation_db")
                db_port = int(os.getenv("MYSQLPORT") or os.getenv("DB_PORT", "3306"))
            
            # Debug: Print connection details on first connection
            # (Commented out to reduce log noise - uncomment if debugging)
            # print(f"Connecting to MySQL: {db_host}:{db_port}/{db_name}")
            
            self.connection = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                port=db_port
            )
            
            if self.connection.is_connected():
                print("Successfully connected to MySQL database")
        
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            self.connection = None
    
    def get_connection(self):
        """Return the database connection"""
        if self.connection and self.connection.is_connected():
            return self.connection
        else:
            # Reconnect if connection was lost
            self.__init__()
            return self.connection
    
    def close(self):
        """Close the database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")