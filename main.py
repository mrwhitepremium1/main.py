from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    # Database logic
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
    
    # Using triple quotes to prevent SyntaxErrors
    welcome_text = f"""Hello 👋 {first_name}!

**Welcome to Mr. White | Official Bot**

💎 **NEW INFO ARRIVED**
━━━━━━━━━━━━━━━━━━━
⭐ **CONFIRMED TICKET** 🎫
☑ **Fixed Tips:** Correct Score
✔ **Safe:** 💯 Guaranteed

**Price:** $20 USD / 150 GHS / 20,000 NGN

To see today's full ticket, please pay via the link and click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. THE CALLBACK HANDLERS (Triple Quotes Applied) ---

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer()
    guide = """📖 **How to Pay Guide**

1️⃣ Click the **Pay via Selar** link.
2️⃣ Select your currency (USD, GHS, NGN, etc.) at the top of the page.
3️⃣ Enter your Name and Email.
4️⃣ Choose your payment method (Card or Mobile Money).
5️⃣ Once payment is successful, return here and click 'I Have Paid (Claim)'."""
    await event.reply(guide)

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer()
    guarantee_text = """🛡️ **Mr. White Win Guarantee**

We pride ourselves on delivering high-accuracy Correct Score selections. Our team performs deep analysis on team form, injuries, and historical data to ensure a **95%+ success rate**.

• **Verified Results:** Every ticket is recorded and verified post-match.
• **Transparency:** We do not delete past results; we let our history speak for itself.
• **Risk Note:** While our accuracy is industry-leading, betting involves risk. We advise responsible play."""
    await event.reply(guarantee_text)

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer()
    terms_text = """⚖️ **Terms of Service**

By utilizing Mr. White Official Bot services, you agree to the following:

1. **Final Sale:** Due to the nature of digital information, all ticket purchases are final. No refunds are issued after a ticket has been accessed.
2. **Verification:** Payment "Claims" are subject to manual admin verification. Fraudulent claims will result in a permanent ban.
3. **Confidentiality:** Sharing or reselling purchased tickets is strictly prohibited and will result in the immediate termination of access."""
    await event.reply(terms_text)

# --- 3. PRICE, SUPPORT, STATUS HANDLERS ---

@client.on(events.NewMessage(pattern='/price'))
async def price(event):
    price_text = """🌍 **Official Price List**
🇺🇸 **USD:** $20
🇬🇭 **GHS:** 150
🇳🇬 **NGN:** 20,000
🇬🇧 **GBP:** £20
🇰🇪 **KES:** 2,000
🇿🇦 **ZAR:** 300
🇿🇲 **ZMW:** 300

✅ *Selar auto-converts to your local currency at checkout.*"""
    await event.reply(price_text)

@client.on(events.NewMessage(pattern='/support'))
async def support(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    await event.reply("📊 **Status:** No active 24h ticket found. Use /start to purchase.")

# --- 4. ADMIN & STARTUP ---

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot is online!")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: Waiting {e.seconds}s...")
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
