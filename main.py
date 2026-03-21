import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_vision', config.API_ID, config.API_HASH)
pending_replies = {}

# --- 1. THE START COMMAND (COVERED PREVIEW) ---
@client.on(events.NewMessage(pattern='/start', incoming=True))
async def start(event):
    if event.sender_id == config.ADMIN_ID: return 
    user = await event.get_sender()
    uid = user.id
    
    # DB Save
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()
    
    # PROFESSIONAL PREVIEW MESSAGE
    welcome_text = (
        f"Hello 👋 {user.first_name}!\n\n"
        "**Welcome to Mr. White | Official Bot**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 **PREMIUM INFO ARRIVED**\n"
        "⭐ **CONFIRMED TICKET** 🎫\n\n"
        "☑ **Fixed Tips:** Correct Score\n"
        "✔ **Verification:** 100% Guaranteed\n\n"
        "To access today's confirmed selections, please check the price via the link below and click '✅ I Have Paid'."
    )
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome_text, buttons=btns)
    
    # Admin Alert
    admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {user.first_name}\nID: `{uid}`", buttons=admin_btns)

# --- 2. THE APPROVAL LOGIC (UNCOVERED TICKET) ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve (24h)", data=f"app_{user.id}")], [Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM**\nID: `{user.id}`", buttons=btns)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid) # Sets 24h expiry in DB
        
        # THE PROFESSIONAL UNCOVERED TICKET MESSAGE
        uncovered_text = (
            "✅ **PAYMENT VERIFIED**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎫 **YOUR OFFICIAL TICKET HAS BEEN ISSUED**\n\n"
            "Your access is now active for **24 Hours**. Please find your confirmed selections on the ticket above.\n\n"
            "🤝 **Good Luck & Stay Disciplined.**"
        )
        
        await event.edit(f"✅ **Approved `{uid}`**")
        # THIS SENDS THE ACTUAL UNCOVERED TICKET
        await client.send_file(uid, config.TICKET_URL, caption=uncovered_text)

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ **Rejected `{uid}`**")
        await client.send_message(uid, "❌ **Verification Failed**\nYour payment could not be verified. Contact support.")

    # [Standard Reply/Block/Cancel logic remains the same...]
    elif data.startswith('qr_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)

# --- 3. THE FIND & BROADCAST COMMANDS ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID, pattern=r'/find (\d+)'))
async def find_user(event):
    uid = int(event.pattern_match.group(1))
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT username, last_seen, approved_until FROM subscribers WHERE user_id = %s", (uid,))
    res = cur.fetchone(); cur.close(); conn.close()
    if res:
        status = "✅ Active" if res[2] and datetime.now() < res[2] else "❌ Inactive"
        await event.reply(f"🔍 **ID:** `{uid}`\n👤 **User:** @{res[0]}\n📊 **Status:** {status}")
    else: await event.reply("❌ Not found.")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
