import psycopg2
import os
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
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
