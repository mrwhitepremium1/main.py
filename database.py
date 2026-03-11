import psycopg2
import os

# This pulls the long link from Railway
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        # This will print in your Railway logs if the variable is missing
        print("🚨 ERROR: DATABASE_URL is not set in Railway Variables!")
        return None
    
    # We add sslmode='require' to ensure a secure network connection
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_connection()
    if conn is None: return
    
    cur = conn.cursor()
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
    print("✅ Database initialized successfully!")
