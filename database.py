import psycopg2
import os
import time

def get_connection():
    # 1. Get the URL from Railway variables
    db_url = os.environ.get("DATABASE_URL")
    
    # 2. Check if the URL is actually there
    if not db_url:
        raise Exception("❌ ERROR: DATABASE_URL is missing from Railway Variables!")

    # 3. Try to connect with a retry loop
    for i in range(3):
        try:
            conn = psycopg2.connect(db_url, connect_timeout=10)
            return conn
        except Exception as e:
            print(f"⚠️ Connection attempt {i+1} failed: {e}")
            time.sleep(2)
            
    raise Exception("❌ Could not connect to Database after 3 tries.")
