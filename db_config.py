import mysql.connector
from mysql.connector import Error
import os

class DatabaseConnection:
    def __init__(self):
        """Initialize database connection"""
        try:
            # Use environment variables for production (Railway), fallback to local values for development
            db_host = os.getenv("DB_HOST", "localhost")
            db_user = os.getenv("DB_USER", "root")
            db_password = os.getenv("DB_PASSWORD", "1234")
            db_name = os.getenv("DB_NAME", "face_animation_db")
            db_port = int(os.getenv("DB_PORT", 3306))
            
            # Debug: Print connection details (password will be hidden in logs)
            print(f"Attempting to connect to MySQL:")
            print(f"  Host: {db_host}")
            print(f"  User: {db_user}")
            print(f"  Database: {db_name}")
            print(f"  Port: {db_port}")
            
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