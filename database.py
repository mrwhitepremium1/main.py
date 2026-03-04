import sqlite3
from datetime import date

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_purchase DATE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reference TEXT,
    amount INTEGER,
    status TEXT,
    created_at DATE
)
""")

conn.commit()

def mark_paid(user_id):
    today = date.today()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, last_purchase) VALUES (?, ?)", (user_id, today))
    conn.commit()

def is_paid(user_id):
    cursor.execute("SELECT last_purchase FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return False
    return row[0] == str(date.today())

def add_payment(user_id, reference, amount, status):
    today = date.today()
    cursor.execute(
        "INSERT INTO payments (user_id, reference, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, reference, amount, status, today)
    )
    conn.commit()