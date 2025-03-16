import sqlite3

DB_FILE = "golf_tournament.db"

def create_database():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS teams (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            player1 TEXT NOT NULL,
                            player2 TEXT NOT NULL,
                            handicap1 REAL NOT NULL,
                            handicap2 REAL NOT NULL,
                            avg_handicap REAL NOT NULL,
                            stableford_points INTEGER DEFAULT 0
                          )''')
        conn.commit()
    print(f"Database '{DB_FILE}' has been created successfully!")

if __name__ == "__main__":
    create_database()