import psycopg2
import os
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    # Force SSL for Railway and use the direct URL
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'pending',
            expiry_time TIMESTAMPTZ
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized successfully!")

# THIS IS THE MISSING PART CAUSING YOUR ERROR
def approve_user_24h(user_id, username):
    expiry = datetime.now() + timedelta(hours=24)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, status, expiry_time) 
        VALUES (%s, %s, 'active', %s)
        ON CONFLICT (user_id) DO UPDATE SET status = 'active', expiry_time = %s
    """, (user_id, username, expiry, expiry))
    conn.commit()
    cur.close()
    conn.close()

def get_active_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE status = 'active' AND expiry_time > NOW()")
    users = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users
