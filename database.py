import os
import psycopg2
from datetime import datetime, timedelta

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            last_seen TIMESTAMP,
            approved_until TIMESTAMP DEFAULT NULL,
            plan_type TEXT DEFAULT 'Free'
        )''')
        # Migration logic to ensure existing DBs are up to date
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS approved_until TIMESTAMP DEFAULT NULL;")
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS plan_type TEXT DEFAULT 'Free';")
        conn.commit()
        print("✅ Database Initialized & Schema Migrated.")
    except Exception as e:
        print(f"❌ Database Error: {e}")
        conn.rollback()
    finally:
        cur.close(); conn.close()

def approve_user_24h(user_id):
    conn = get_connection(); cur = conn.cursor()
    expiry = datetime.now() + timedelta(hours=24)
    cur.execute("UPDATE subscribers SET approved_until = %s WHERE user_id = %s", (expiry, user_id))
    conn.commit(); cur.close(); conn.close()

def is_user_approved(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT approved_until FROM subscribers WHERE user_id = %s", (user_id,))
    res = cur.fetchone(); cur.close(); conn.close()
    return res and res[0] and datetime.now() < res[0]
