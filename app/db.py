# app/db.py
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',  # Replace with your MySQL host
        user='your_username_here',  # Replace with your MySQL username
        password='your_password_here',  # Replace with your MySQL password
        database='your_database_name_here'  # Replace with your database name
    )