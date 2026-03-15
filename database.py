import psycopg2
import os
import time

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL missing from Railway Variables!")
    
    for i in range(3):
        try:
            # Using the URL directly to avoid socket errors
            return psycopg2.connect(db_url, connect_timeout=10)
        except Exception as e:
            print(f"⚠️ Connection attempt {i+1} failed. Retrying...")
            time.sleep(2)
    raise Exception("❌ Could not connect to Database.")

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Create the subscribers table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            approved BOOLEAN DEFAULT FALSE,
            expiry_time TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Ensure the last_seen column exists (Self-healing)
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database Initialized Successfully")

def is_user_approved(user_id):
    from datetime import datetime
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT approved, expiry_time FROM subscribers WHERE user_id = %s", (user_id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    if res and res[0]:
        if res[1] and res[1] > datetime.now():
            return True
    return False

def approve_user_24h(user_id, username):
    from datetime import datetime, timedelta
    expiry = datetime.now() + timedelta(hours=24)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, approved, expiry_time)
        VALUES (%s, %s, TRUE, %s)
        ON CONFLICT (user_id) DO UPDATE SET approved = TRUE, expiry_time = %s
    """, (user_id, username, expiry, expiry))
    conn.commit()
    cur.close()
    conn.close()
