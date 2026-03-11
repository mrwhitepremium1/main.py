from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & PRICE COMMANDS (Standardized Pricing) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    # Ensure user is in subscribers
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
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

@client.on(events.NewMessage(pattern='/price'))
async def price_cmd(event):
    price_text = """🌍 **Mr. White Official Price List**
*(Daily Access - Correct Score Ticket)*

🇺🇸 **USD:** $20
🇬🇭 **GHS:** 150 GHS
🇳🇬 **NGN:** 20,000 NGN

✅ **Pay here:** https://selar.co/mrwhite"""
    await event.reply(price_text)

# --- 2. STATUS CHECK (Fixed for Post-Purchase) ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # This now checks the database for actual 24h approval
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE**. You have full access to current tickets.")
    else:
        await event.reply("📊 **Status:** Your access is currently **INACTIVE**. Please purchase a ticket to activate.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- 3. AUTOMATED ASSISTANT (Fixed "Random Message") ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_reply(event):
    # Only trigger if the message is NOT a command
    if event.text.startswith('/') or event.sender_id == config.ADMIN_ID:
        return

    assistant_buttons = [
        [Button.inline("🎫 View Ticket", data="trigger_start")],
        [Button.inline("💰 Price List", data="trigger_price")]
    ]
    await event.reply("🤖 **Mr. White Assistant:** How can I help you today?", buttons=assistant_buttons)

# Callback handlers for the automated assistant buttons
@client.on(events.CallbackQuery(data="trigger_start"))
async def cb_start(event):
    await event.answer()
    await start(event)

@client.on(events.CallbackQuery(data="trigger_price"))
async def cb_price(event):
    await event.answer()
    await price_cmd(event)

# --- 4. ADMIN & CALLBACK HANDLERS ---
@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay(event):
    await event.answer()
    guide = """📖 **How to Pay Guide**
1️⃣ Click the **Pay via Selar** link.
2️⃣ Select your currency (USD, GHS, NGN) at the top.
3️⃣ Pay via Card or Mobile Money.
4️⃣ Return here and click **'I Have Paid (Claim)'**."""
    await event.reply(guide)

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), 
             Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    data = event.data.decode().split('_')
    action, uid = data[0], int(data[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been successfully issued and is valid for 24 hours.")
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

# --- 5. STARTUP ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot fully updated and online.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
