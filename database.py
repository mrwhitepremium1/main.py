import psycopg2
import os
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # expiry_time stores when their access should end
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

def add_subscriber(user_id, username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, username))
    conn.commit()
    cur.close()
    conn.close()

def approve_user_24h(user_id):
    """Sets status to active and sets expiry to 24 hours from now"""
    expiry = datetime.now() + timedelta(hours=24)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE subscribers SET status = 'active', expiry_time = %s WHERE user_id = %s",
        (expiry, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def remove_expired_users():
    """Finds users whose expiry_time has passed and resets them"""
    conn = get_connection()
    cur = conn.cursor()
    # Find users to notify before deleting/resetting (optional)
    cur.execute("SELECT user_id FROM subscribers WHERE status = 'active' AND expiry_time < NOW()")
    expired_ids = [row[0] for row in cur.fetchall()]
    
    # Reset their status
    cur.execute("UPDATE subscribers SET status = 'expired' WHERE status = 'active' AND expiry_time < NOW()")
    conn.commit()
    cur.close()
    conn.close()
    return expired_ids
