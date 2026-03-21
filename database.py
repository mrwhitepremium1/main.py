def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Create the full table if it doesn't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        last_seen TIMESTAMP,
        approved_until TIMESTAMP DEFAULT NULL,
        plan_type TEXT DEFAULT 'Free'
    )''')
    
    # Forcefully add columns in case the table already existed without them
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS approved_until TIMESTAMP DEFAULT NULL;")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS plan_type TEXT DEFAULT 'Free';")
    
    conn.commit()
    cur.close()
    conn.close()
