import psycopg2
import os
import time
from datetime import datetime, timedelta

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL missing!")
    
    # Retry loop: Try 5 times before giving up
    for attempt in range(5):
        try:
            # Increased timeout to 20 seconds for stability
            return psycopg2.connect(db_url, connect_timeout=20)
        except psycopg2.OperationalError as e:
            print(f"⚠️ Connection attempt {attempt + 1} failed. Retrying in 3s...")
            time.sleep(3)
    
    raise Exception("❌ Total Connection Timeout. Database is unresponsive.")

def init_db():
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                approved BOOLEAN DEFAULT FALSE,
                expiry_time TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Self-healing columns
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS expiry_time TIMESTAMP")
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit(); cur.close(); conn.close()
        print("✅ Database Verified & Active")
    except Exception as e:
        print(f"❌ DB Init Error: {e}")

# ... (Keep your is_user_approved and approve_user_24h functions the same)
