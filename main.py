import os
import asyncio
from telethon import TelegramClient, events
import database

# --- 1. SETUP CREDENTIALS ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Added connection_retries and retry_delay to beat the TimeoutError
client = TelegramClient('bot_session', API_ID, API_HASH, 
                        connection_retries=None, 
                        retry_delay=5)

# --- 2. THE START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = (
        "👋 **Welcome to the Signal Service!**\n\n"
        "Our automated bot is currently undergoing maintenance. To get your access immediately:\n\n"
        "🔗 **Pay via Selar (Instant):**\n"
        "https://selar.co/mrwhite\n\n"
        "📩 **Direct Admin Support:**\n"
        "@best_admin24\n\n"
        "Please send your proof of payment to the admin above for manual activation!"
    )
    await event.respond(msg)

# --- 3. THE PROPER RUN LOOP ---
async def main():
    database.init_db()
    
    print("⏳ Attempting to connect to Telegram...")
    try:
        # We use a try/except here to catch that specific Timeout
        await client.start(bot_token=BOT_TOKEN)
        print("🚀 Bot is online and stable in Maintenance Mode!")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"⚠️ Connection hit a snag: {e}")
        print("🔄 Railway will auto-restart in a moment to try again.")

if __name__ == '__main__':
    asyncio.run(main())
