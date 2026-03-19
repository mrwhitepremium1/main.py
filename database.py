import os
import psycopg2
from datetime import datetime, timedelta

def get_connection():
    # Gets the DB URL from your environment (Heroku/Railway/VPS)
    db_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Table for all users
    cur.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        last_seen TIMESTAMP,
        approved_until TIMESTAMP DEFAULT NULL,
        plan_type TEXT DEFAULT 'Free'
    )''')
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database Initialized")

def approve_user_24h(user_id, plan="Premium"):
    conn = get_connection()
    cur = conn.cursor()
    expiry = datetime.now() + timedelta(hours=24)
    cur.execute('''UPDATE subscribers 
                   SET approved_until = %s, plan_type = %s 
                   WHERE user_id = %s''', (expiry, plan, user_id))
    conn.commit()
    cur.close()
    conn.close()

def is_user_approved(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT approved_until FROM subscribers WHERE user_id = %s", (user_id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    
    if res and res[0]:
        # Checks if the current time is still before the expiry time
        return datetime.now() < res[0]
    return False

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username FROM subscribers")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users
