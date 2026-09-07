import os
import sqlite3

# database.db lives in the project root (one level up from the app/ package)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all required tables automatically if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            password TEXT NOT NULL,
            state TEXT,
            chat_id TEXT,
            age TEXT,
            gender TEXT,
            area TEXT,
            city TEXT,
            blood_group TEXT,
            diseases TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


# Ensure tables exist as soon as this module is imported
init_db()
