# A simple set to keep track of approved IDs while the bot is running
approved_users = set()

def init_db():
    print("✅ Memory Mode: Database bypassed. Bot is stable.")

def is_user_approved(user_id):
    # Returns True if the user is in our memory list
    return user_id in approved_users

def approve_user_24h(user_id, username=None):
    # Adds the user to the list
    approved_users.add(user_id)
    print(f"✅ User {user_id} added to active session.")
