import psycopg2
import os
from datetime import datetime, timedelta

def get_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approved_users (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            expiry_time TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables initialized successfully.")

def approve_user_24h(user_id, name):
    conn = get_connection()
    cur = conn.cursor()
    expiry = datetime.now() + timedelta(hours=24)
    cur.execute("""
        INSERT INTO approved_users (user_id, name, expiry_time)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) 
        DO UPDATE SET expiry_time = EXCLUDED.expiry_time
    """, (user_id, name, expiry))
    conn.commit()
    cur.close()
    conn.close()

def is_user_approved(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT expiry_time FROM approved_users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result and datetime.now() < result[0]:
        return True
    return False
