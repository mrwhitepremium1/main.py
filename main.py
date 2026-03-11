import asyncio
from telethon import TelegramClient, events, Button
import config
import database

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

# --- NEW: BACKGROUND TASK FOR EXPIRY ---
async def expiry_checker():
    while True:
        expired_users = database.remove_expired_users()
        for user_id in expired_users:
            try:
                await client.send_message(user_id, "⏰ **Your 24-hour access has expired.**\nPlease pay again to get today's ticket!")
            except:
                pass
        await asyncio.sleep(1800) # Check every 30 minutes

# --- ADMIN: APPROVAL (Updated to use 24h logic) ---
@client.on(events.CallbackQuery(pattern=r"approve_(.*)"))
async def approve_logic(event):
    if event.sender_id != config.ADMIN_ID: return
    user_id = int(event.data.decode().split("_")[1])
    
    database.approve_user_24h(user_id) # Set 24h timer
    await client.send_file(user_id, config.TICKET_IMAGE, caption="✅ **Verified!** You have 24 hours of access.")
    await event.edit(f"User {user_id} approved for 24 hours.")

# --- MAIN RUN ---
database.init_db()
client.loop.create_task(expiry_checker()) # Start the clock
print("Bot is live with 24h Expiry System...")
client.run_until_disconnected()
