import os
import psycopg2
from psycopg2 import pool

# Create a connection pool so the bot doesn't have to "re-login" every time
try:
    db_url = os.environ.get("DATABASE_URL")
    postgreSQL_pool = psycopg2.pool.SimpleConnectionPool(1, 20, db_url)
    print("✅ Connection pool created successfully")
except Exception as e:
    print(f"❌ Error creating pool: {e}")

def get_connection():
    return postgreSQL_pool.getconn()

def return_connection(conn):
    postgreSQL_pool.putconn(conn)

def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users 
                       (user_id BIGINT PRIMARY KEY, 
                        username TEXT, 
                        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        cur.close()
        print("✅ Database Tables Verified!")
    finally:
        return_connection(conn)

def is_user_approved(user_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        return res is not None
    finally:
        return_connection(conn)

def approve_user(user_id, username=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, username))
        conn.commit()
        cur.close()
    finally:
        return_connection(conn)

# New function for your Broadcast!
def get_all_users():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        users = [row[0] for row in cur.fetchall()]
        cur.close()
        return users
    finally:
        return_connection(conn)
