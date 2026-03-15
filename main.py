import os
import asyncio
from telethon import TelegramClient, events
import database

# --- 1. SETUP CREDENTIALS ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Client initialization without starting immediately
client = TelegramClient('bot_session', API_ID, API_HASH)

# --- 2. THE START COMMAND (Maintenance Mode) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = (
        "👋 **Welcome to the Signal Service!**\n\n"
        "Our automated payment bot is currently undergoing maintenance. To get your access immediately, please use the options below:\n\n"
        "🔗 **Pay via Selar (Instant):**\n"
        "https://selar.co/mrwhite\n\n"
        "📩 **Direct Admin Support:**\n"
        "@best_admin24\n\n"
        "**Note:** Please send your proof of payment to the admin above for manual activation. Thank you for your patience!"
    )
    await event.respond(msg)

# --- 3. THE PROPER RUN LOOP ---
async def main():
    database.init_db()
    # Correctly starting the client inside the async loop
    await client.start(bot_token=BOT_TOKEN)
    print("🚀 Bot is online and stable in Maintenance Mode!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
