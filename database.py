import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'pending'
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

def update_status(user_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET status = %s WHERE user_id = %s", (status, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_all_active_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE status = 'active'")
    users = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users
