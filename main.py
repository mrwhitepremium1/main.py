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
client = TelegramClient('mr_white_final_v16', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. ADMIN COMMANDS ---

# UPDATED BROADCAST: Now more sensitive to triggers
@client.on(events.NewMessage(pattern=r'^/(broadcast|boardcast)(.*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    
    # Extract message from the event
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    
    if not msg_text and not photo:
        return await event.reply("❌ **Error:** Please provide a message or photo.\nUsage: `/broadcast Hello everyone!`")
        
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
            await asyncio.sleep(0.1) # Essential to avoid FloodWait
        except (UserIsBlockedError, PeerIdInvalidError):
            blocked += 1
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
    for r in rows:
        res += f"• `{r[0]}` | @{r[1] if r[1] else 'N/A'}\n"
    await event.reply(res)

# --- 2. SUPPORT & REPLIES ---

@client.on(events.NewMessage())
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        uid = event.sender_id
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        await client.send_message(config.ADMIN_ID, f"📩 **MESSAGE FROM:** `{uid}`")
        await client.forward_messages(config.ADMIN_ID, event.message)

@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    uid, msg = int(event.pattern_match.group(1)), event.pattern_match.group(2).strip()
    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg}")
        await event.reply(f"✅ Sent to `{uid}`")
    except: await event.reply("❌ User has blocked the bot.")

# --- 3. START & CALLBACKS ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    try: database.approve_user_24h(user.id, user.username)
    except: pass
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption="**Welcome to Mr. White Official!**", buttons=btns)

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    user = await event.get_sender()
    await event.answer("✅ Sent to Admin.", alert=True)
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{user.id}`", buttons=btns)

# --- 4. RUNNER ---
async def main():
    try:
        database.init_db()
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT IS LIVE & BROADCAST FIXED!")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__': asyncio.run(main())
