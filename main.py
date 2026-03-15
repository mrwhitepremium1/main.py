import os
import asyncio
from telethon import TelegramClient, events
import database

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = 7461971701  # Replace with your actual Telegram ID

client = TelegramClient('bot_session', API_ID, API_HASH, connection_retries=None)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # This automatically adds every new person to your DB list
    database.approve_user(event.sender_id, event.sender.username)
    
    msg = (
        "👋 **Welcome to Mr. White Signals!**\n\n"
        "🔗 **New Ticket Link:** https://selar.co/mrwhite?v=2\n"
        "📩 **Admin:** @best_admin24\n\n"
        "Check your status with /status"
    )
    await event.respond(msg)

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != ADMIN_ID:
        return

    command_text = event.message.text.split(' ', 1)
    if len(command_text) < 2:
        return await event.respond("❌ Usage: `/broadcast Hello everyone!`")

    broadcast_msg = command_text[1]
    all_users = database.get_all_users()
    
    await event.respond(f"🚀 Sending to {len(all_users)} users...")
    
    count = 0
    for user_id in all_users:
        try:
            await client.send_message(user_id, broadcast_msg)
            count += 1
            await asyncio.sleep(0.05) # Prevent Telegram spam flood
        except Exception:
            pass
            
    await event.respond(f"✅ Broadcast complete! Sent to {count} users.")

async def main():
    database.init_db()
    await client.start(bot_token=BOT_TOKEN)
    print("🚀 BOT IS FULLY REPAIRED!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
