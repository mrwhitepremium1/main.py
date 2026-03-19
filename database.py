import psycopg2
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_connection():
    # Railway automatically provides DATABASE_URL
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Table 1: General User Tracking & AI Memory
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_hot BOOLEAN DEFAULT FALSE,
            memory TEXT DEFAULT ''
        )
    """)
    # Table 2: VIP Access Tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approved_users (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            expiry_time TIMESTAMP,
            approved BOOLEAN DEFAULT TRUE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database tables initialized.")

def get_user_memory(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT memory FROM subscribers WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row[0] if row else ""

def save_user_memory(user_id, memory_text):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE subscribers SET memory=%s WHERE user_id=%s", (memory_text, user_id))
    conn.commit(); cur.close(); conn.close()

def mark_hot_lead(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE subscribers SET is_hot=TRUE WHERE user_id=%s", (user_id,))
    conn.commit(); cur.close(); conn.close()

def approve_user_24h(user_id, name="User"):
    conn = get_connection(); cur = conn.cursor()
    expiry = datetime.now() + timedelta(hours=24)
    cur.execute("""
        INSERT INTO approved_users (user_id, name, expiry_time, approved)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (user_id) DO UPDATE 
        SET expiry_time = EXCLUDED.expiry_time, approved = TRUE
    """, (user_id, name, expiry))
    conn.commit(); cur.close(); conn.close()