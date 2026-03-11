import psycopg2
import os
from datetime import datetime, timedelta

def get_connection():
    # Railway provides the DATABASE_URL automatically
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Table for tracking all visitors (for Visitor Alerts & Broadcasts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Table for approved/paid users (24-hour access)
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

def add_subscriber(user_id, username):
    """Saves a visitor to the database if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username) 
        VALUES (%s, %s) 
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username))
    conn.commit()
    cur.close()
    conn.close()

def approve_user_24h(user_id, name):
    """Grants a user 24 hours of access."""
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
    """Checks if a user still has active 24-hour access."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT expiry_time FROM approved_users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        expiry_time = result[0]
        if datetime.now() < expiry_time:
            return True
    return False
