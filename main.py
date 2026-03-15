import os
import asyncio
from telethon import TelegramClient, events
import database  # Make sure your database.py is the "Stable" version we made

# --- 1. SETUP ENGINE ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- 2. THE START COMMAND (Maintenance Mode) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = (
        "👋 **Welcome to the Signal Service!**\n\n"
        "The bot is currently under maintenance for upgrades. To get your access immediately:\n\n"
        "🔗 **Pay via Selar:** [PASTE_YOUR_SELAR_LINK_HERE]\n"
        "📩 **DM for Approval:** @[YOUR_USERNAME]\n\n"
        "Please send your proof of payment to the admin above for manual activation! Thank you for your patience."
    )
    await event.respond(msg)

# --- 3. RUN THE BOT ---
async def main():
    database.init_db()
    print("🚀 Bot is online in Maintenance Mode!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
