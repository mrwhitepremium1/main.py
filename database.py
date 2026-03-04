import sqlite3

# Connect to SQLite database
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    paid INTEGER DEFAULT 0
)
""")

# Payments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reference TEXT,
    amount INTEGER,
    status TEXT
)
""")

conn.commit()

# -------------------------------
# Functions
# -------------------------------
def mark_paid(user_id):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, paid) VALUES (?, ?)", (user_id, 1))
    conn.commit()

def is_paid(user_id):
    cursor.execute("SELECT paid FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def add_payment(user_id, reference, amount, status="pending"):
    cursor.execute("INSERT INTO payments (user_id, reference, amount, status) VALUES (?, ?, ?, ?)",
                   (user_id, reference, amount, status))
    conn.commit()
