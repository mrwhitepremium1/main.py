import os
import asyncio
from telethon import TelegramClient, events, Button
import database

# --- 1. SETUP ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = 7461971701  # Your Numeric Telegram ID

client = TelegramClient('bot_session', API_ID, API_HASH, connection_retries=None)

# --- 2. COMMANDS ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # Automatically track new users in the database
    database.approve_user(event.sender_id, event.sender.username)
    
    msg = (
        "👋 **Welcome to Mr. White Signals!**\n\n"
        "🔗 **New Ticket Link:** https://selar.co/mrwhite?v=2\n"
        "📩 **Admin:** @best_admin24\n\n"
        "Check your status with /status"
    )
    await event.respond(msg)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.respond("📊 **Status: Active** 🤝\n\nYour subscription is currently active.")
    else:
        await event.respond("❌ **Status: Inactive**\nPlease purchase a ticket or contact @best_admin24.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.respond("💬 **You're now connected to support.**\nKindly explain your issue clearly. Mr. White is listening. 🎯")

# --- 3. BUTTON LOGIC (THE FIX) ---

@client.on(events.CallbackQuery())
async def callback(event):
    data = event.data.decode()
    
    # Handle Approve Click
    if data.startswith('approve_'):
        user_id = int(data.split('_')[1])
        database.approve_user(user_id) # Save to Postgres
        
        await event.answer("✅ User Approved!", alert=True)
        await event.edit(f"✅ User {user_id} has been activated in the database.")
        
        try:
            await client.send_message(user_id, "🎊 **Great news!** Your payment has been verified. Your subscription is now **ACTIVE** ✅.")
        except:
            pass

    # Handle Reject Click
    elif data.startswith('reject_'):
        user_id = int(data.split('_')[1])
        await event.answer("❌ Payment Rejected", alert=True)
        await event.edit(f"❌ Payment claim for {user_id} was rejected.")
        
        try:
            await client.send_message(user_id, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Please contact @best_admin24 for assistance.")
        except:
            pass

# --- 4. BROADCAST SYSTEM ---

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != ADMIN_ID:
        return

    command_text = event.message.text.split(' ', 1)
    if len(command_text) < 2:
        return await event.respond("❌ Usage: `/broadcast Your message here` ")

    broadcast_msg = command_text[1]
    all_users = database.get_all_users()
    
    await event.respond(f"🚀 Sending to {len(all_users)} users...")
    
    count = 0
    for user_id in all_users:
        try:
            await client.send_message(user_id, broadcast_msg)
            count += 1
            await asyncio.sleep(0.05) # Prevent Flood
        except:
            pass
            
    await event.respond(f"✅ Broadcast complete! Sent to {count} users.")

# --- 5. RUN ---
async def main():
    database.init_db()
    await client.start(bot_token=BOT_TOKEN)
    print("🚀 BOT IS FULLY REPAIRED & LIVE!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
