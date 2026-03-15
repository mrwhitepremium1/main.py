# database.py - Stable Version (No Postgres)

def init_db():
    # We are skipping the database to prevent timeouts
    print("✅ System: Running in Manual Mode. Stability 100%.")

def is_user_approved(user_id):
    # Always return False for now, or True if you want to bypass
    return False

def approve_user_24h(user_id, username=None):
    # This just prints to the logs since we are doing manual DMs
    print(f"✅ Manual Request: User {user_id} wants approval.")
