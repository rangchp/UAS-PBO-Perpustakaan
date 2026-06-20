import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',        
    'database': 'perpustakaan'
}

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn
