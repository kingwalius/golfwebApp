import sqlite3

DB_FILE = "golf_tournament.db"

try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:", tables)
    conn.close()
except Exception as e:
    print("Database error:", e)