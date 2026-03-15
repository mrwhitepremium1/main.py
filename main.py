import logging
import os
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
# Session name changed to ensure a fresh start
client = TelegramClient('mr_white_final_v5', config.API_ID, config.API_HASH, connection_retries=None)

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
            await asyncio.sleep(0.3)
        except (UserIsBlockedError, PeerIdInvalidError):
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
            conn.commit(); cur.close(); conn.close()
            blocked_count += 1
        except Exception: continue
        
    await progress_msg.edit(f"✅ **Broadcast complete!**\nSent: **{success_count}**\nRemoved: **{blocked_count}**")

# --- 2. START COMMAND (No Guarantee/Terms Buttons) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    # FIXED: Using the correct function name from your database module
    try:
        database.approve_user_24h(user.id, user.username)
    except Exception as e:
        logging.error(f"Database error on start: {e}")

    # Menu with ONLY Payment and "I Have Paid"
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
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    # Bold text as requested
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 4. CALLBACKS & ADMIN ACTIONS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    
    if data == "claim_pay":
        await event.answer("✅ Sent to Admin.", alert=True)
        user = await event.get_sender()
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved User {uid}")
        try:
            await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued for 24 hours.")
        except: pass

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected User {uid}")
        reject_msg = (
            "❌ **Payment Claim Rejected**\n\n"
            "Your payment could not be verified at this time.\n"
            "Please contact Mr White for assistance.\n\n"
            "Command: /support"
        )
        try:
            await client.send_message(uid, reject_msg)
        except: pass

# --- 5. RUNNER (With Flood Protection) ---
async def main():
    try:
        database.init_db()
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT IS LIVE, REPAIRED, & SYNCHRONIZED!")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: Waiting {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
