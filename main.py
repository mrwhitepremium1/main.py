import logging
import os
import asyncio
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
# Use connection_retries=None for better stability on Railway
client = TelegramClient('mr_white_production', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. BROADCAST SYSTEM ---
@client.on(events.NewMessage(pattern=r'/(broadcast|boardcast)([\s\S]*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    
    if not msg_text and not photo:
        await event.reply("❌ **Error:** Please type a message after the command.")
        return
        
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    progress_msg = await event.reply(f"📣 **Broadcasting...**")
    success_count = 0; blocked_count = 0
    
    for user in users:
        uid = user[0]
        try:
            if photo: await client.send_file(uid, photo, caption=msg_text)
            else: await client.send_message(uid, msg_text)
            success_count += 1
            await asyncio.sleep(0.3) # Avoid flood
        except (UserIsBlockedError, PeerIdInvalidError):
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
            conn.commit(); cur.close(); conn.close()
            blocked_count += 1
        except Exception: continue
        
    await progress_msg.edit(f"✅ **Broadcast complete!**\nSent: **{success_count}**\nRemoved: **{blocked_count}**")

# --- 2. START COMMAND (Clean Menu) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    now = datetime.now()
    
    # Track User
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, last_seen) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) DO UPDATE SET last_seen = EXCLUDED.last_seen, username = EXCLUDED.username
    """, (user.id, user.username, now))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()

    # Admin Alert
    alert = (f"👤 **Visitor Alert!**\nName: {first_name}\nUsername: @{user.username if user.username else 'N/A'}\n"
             f"ID: `{user.id}`\nTotal Users: {total}")
    await client.send_message(config.ADMIN_ID, alert)

    # Clean Menu: Guarantee & Terms buttons removed
    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check "
                    f"the price via the link below and click **'I Have Paid'**.")
    
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. STATUS & BOLD SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # Fixed to use exact wording from your request
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    # Exact wording with bold as requested
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 4. CALLBACKS & ADMIN APPROVAL ---
@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer(); act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if act == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued and will remain valid for 24 hours.")
        await event.edit(f"✅ Approved User {uid}")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nPlease contact Mr White for assistance.")
        await event.edit(f"❌ Rejected User {uid}")

# --- 5. RUNNER ---
async def main():
    try:
        database.init_db()
        # Database Maintenance
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit(); cur.close(); conn.close()
        
        await client.start(bot_token=config.BOT_TOKEN)
        print("✅ DATABASE CONNECTION SUCCESSFUL!")
        print("🚀 BOT IS FULLY REPAIRED!")
        await client.run_until_disconnected()
    except FloodWaitError as e: 
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
