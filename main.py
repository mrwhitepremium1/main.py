from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

# Initialize Client
client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\n\nName: {first_name}\nUsername: @{user.username}\n📈 Total Users: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\n"
                    "💎 **NEW INFO ARRIVED**\n━━━━━━━━━━━━━━━━━━━\n"
                    "⭐ **CONFIRMED TICKET** 🎫\n☑ **Fixed Tips:** Correct Score\n✔ **Safe:** 💯 Guaranteed\n\n"
                    "**Price:** $20 USD / 150 GHS / 20,000 NGN\n\n"
                    "To see today's full ticket, please pay via the link and click 'Claim'.")
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. THE FIX: CALLBACK HANDLERS (Stops "Loading..." Spinner) ---

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer() # CRITICAL: This stops the loading spinner
    guide = (
        "📖 **How to Pay Guide**\n\n"
        "1️⃣ Click the **Pay via Selar** link.\n"
        "2️⃣ Select your currency (USD, GHS, NGN, etc.) at the top of the page.\n"
        "3️⃣ Enter your Name and Email.\n"
        "4️⃣ Choose your payment method (Card or Mobile Money).\n"
        "5️⃣ Once payment is successful, return here and click **'I Have Paid (Claim)'**."
    )
    await event.reply(guide)

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer() # Stops loading spinner
    guarantee_text = (
        "🛡️ **Mr. White Win Guarantee**\n\n"
        "We pride ourselves on delivering high-accuracy Correct Score selections. "
        "Our team performs deep analysis on team form, injuries, and historical data to ensure a **95%+ success rate**.\
