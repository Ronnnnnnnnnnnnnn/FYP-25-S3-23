import mysql.connector
from mysql.connector import Error
import os

class DatabaseConnection:
    def __init__(self):
        """Initialize database connection"""
        try:
            # Use environment variables for production (Railway), fallback to local values for development
            self.connection = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", "1234"),
                database=os.getenv("DB_NAME", "face_animation_db"),
                port=int(os.getenv("DB_PORT", 3306))
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