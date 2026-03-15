import psycopg2
import os
import time
from datetime import datetime, timedelta

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL missing!")
    # Using a 10-second timeout to prevent button lag
    return psycopg2.connect(db_url, connect_timeout=10)

def init_db():
    conn = get_connection(); cur = conn.cursor()
    # 1. Create table if it's a fresh start
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            approved BOOLEAN DEFAULT FALSE,
            expiry_time TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 2. Self-Healing: Add columns if they are missing from old versions
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS expiry_time TIMESTAMP")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    conn.commit(); cur.close(); conn.close()
    print("✅ Database Verified: Approval system active.")

def is_user_approved(user_id):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT approved, expiry_time FROM subscribers WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close(); conn.close()
        
        if res:
            is_approved, expiry = res[0], res[1]
            # Check if they are marked approved AND the 24 hours hasn't passed
            if is_approved and expiry and expiry > datetime.now():
                return True
        return False
    except Exception as e:
        print(f"Error checking approval: {e}")
        return False

def approve_user_24h(user_id, username):
    # Set expiry to exactly 24 hours from right now
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
    print(f"✅ User {user_id} approved. Expiry set to: {expiry}")
