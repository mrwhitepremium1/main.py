import os
import psycopg2
import time

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    # Try to connect with a 10 second timeout
    return psycopg2.connect(db_url, connect_timeout=10)

def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users 
                       (user_id BIGINT PRIMARY KEY, 
                        username TEXT, 
                        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"⚠️ Database not ready yet, but bot will stay online. Error: {e}")

def is_user_approved(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except:
        return False # Fail safely

def approve_user(user_id, username=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Could not save user to DB: {e}")

def get_all_users():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        users = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return users
    except:
        return []
