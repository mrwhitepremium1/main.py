import psycopg2
import os
import time
from datetime import datetime, timedelta

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL missing!")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection(); cur = conn.cursor()
    # Ensure all necessary columns exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            approved BOOLEAN DEFAULT FALSE,
            expiry_time TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Self-healing for existing databases
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS expiry_time TIMESTAMP")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit(); cur.close(); conn.close()
    print("✅ Database Initialized & Verified")

def is_user_approved(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT approved, expiry_time FROM subscribers WHERE user_id = %s", (user_id,))
    res = cur.fetchone()
    cur.close(); conn.close()
    
    if res:
        is_approved, expiry = res[0], res[1]
        # If they are approved AND the time hasn't run out
        if is_approved and expiry and expiry > datetime.now():
            return True
    return False

def approve_user_24h(user_id, username):
    expiry = datetime.now() + timedelta(hours=24)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, approved, expiry_time, last_seen)
        VALUES (%s, %s, TRUE, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET 
            approved = TRUE, 
            expiry_time = EXCLUDED.expiry_time,
            username = EXCLUDED.username,
            last_seen = EXCLUDED.last_seen
    """, (user_id, username, expiry, datetime.now()))
    conn.commit(); cur.close(); conn.close()
    print(f"✅ User {user_id} approved for 24h")
