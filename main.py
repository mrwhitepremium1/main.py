import logging
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been reviewed and will be seen soon! 🎯"
last_notified = {} 

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v17_final', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. ADMIN COMMANDS (Broadcast & Management) ---

@client.on(events.NewMessage(pattern=r'^/(broadcast|boardcast)(.*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    if not msg_text and not photo:
        return await event.reply("❌ **Error:** Usage: `/broadcast Hello!`")
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    status_msg = await event.reply(f"📣 **Sending to {len(users)} users...**")
    success, blocked = 0, 0
    for user in users:
        try:
            if photo: await client.send_file(user[0], photo, caption=msg_text)
            else: await client.send_message(user[0], msg_text)
            success += 1
            await asyncio.sleep(0.1) 
        except (UserIsBlockedError, PeerIdInvalidError): blocked += 1
        except Exception: continue
    await status_msg.edit(f"✅ **Broadcast Done**\nSent: `{success}`\nBlocked: `{blocked}`")

@client.on(events.NewMessage(pattern=r'/sleep (on|off|of)'))
async def toggle_sleep(event):
    global sleep_mode_active
    if event.sender_id != config.ADMIN_ID: return
    val = event.pattern_match.group(1).lower()
    sleep_mode_active = (val == "on")
    await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

@client.on(events.NewMessage(pattern=r'/users?'))
async def list_users(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id, username FROM subscribers ORDER BY last_seen DESC LIMIT 10")
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    res = f"📊 **Total Subscribers:** `{total}`\n\n"
    for r in rows: res += f"• `{r[0]}` | @{r[1] if r[1] else 'N/A'}\n"
    await event.reply(res)

# --- 2. USER COMMANDS (Status & Support - FIXED) ---

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    is_approved = database.is_user_approved(event.sender_id)
    if is_approved:
        await event.reply("📊 **Status: Active 🤝**\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 **Status: Inactive ❌**\n\nPlease purchase a ticket to activate access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 3. APPROVE & REJECT BUTTONS (FIXED) ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        # Match callback prefix for the next step
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), 
                 Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{user.id}`", buttons=btns)
    
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ **User {uid} Approved.**")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!**\nYour ticket is now active.")
        
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ **User {uid} Rejected.**")
        await client.send_message(uid, "❌ **Payment Rejected.**\nContact support if this is a mistake.")

# --- 4. MESSAGE FORWARDING ---

@client.on(events.NewMessage())
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        uid = event.sender_id
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤 ID: `{uid}`")
        await client.forward_messages(config.ADMIN_ID, event.message)

@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    uid, msg = int(event.pattern_match.group(1)), event.pattern_match.group(2).strip()
    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg}")
        await event.reply(f"✅ Reply sent to `{uid}`")
    except: await event.reply("❌ Could not send reply.")

# --- 5. START COMMAND ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    # Ensure user is in database
    try: database.approve_user_24h(user.id, user.username) 
    except: pass
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption="**Welcome to Mr. White Official!**", buttons=btns)

# --- RUNNER ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
