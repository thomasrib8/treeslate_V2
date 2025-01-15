import sqlite3
import os
from datetime import datetime

DB_PATH = "translated_files.db"

def init_db():
    """
    Initialize the database and create the `translated_files` table if it doesn't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translated_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            date_created TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_translated_file(file_name, file_path):
    """
    Add a translated file's details to the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO translated_files (file_name, file_path, date_created)
        VALUES (?, ?, ?)
    """, (file_name, file_path, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_translated_files():
    """
    Retrieve all translated files from the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT file_name, file_path, date_created FROM translated_files
        ORDER BY date_created DESC
    """)
    files = cursor.fetchall()
    conn.close()
    return files
