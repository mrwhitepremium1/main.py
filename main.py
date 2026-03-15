import logging
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS & CACHE ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been reviewed and will be seen soon! 🎯"
last_notified = {} # Prevents admin spam

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_v13', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. ADMIN MANAGEMENT ---
@client.on(events.NewMessage(pattern=r'/sleep (on|off)'))
async def toggle_sleep(event):
    global sleep_mode_active
    if event.sender_id != config.ADMIN_ID: return
    sleep_mode_active = (event.pattern_match.group(1).lower() == "on")
    await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

@client.on(events.NewMessage(pattern='/users'))
async def list_users(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id, username, last_seen FROM subscribers ORDER BY last_seen DESC LIMIT 15")
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    
    response = f"📊 **Total Subscribers:** `{total}`\n\n**Recent Activity:**\n"
    for r in rows:
        last_active = r[2].strftime("%Y-%m-%d %H:%M") if r[2] else "Unknown"
        response += f"• `{r[0]}` | @{r[1] if r[1] else 'N/A'}\n  └ 🕒 {last_active}\n"
    await event.reply(response)

# --- 2. FORWARDING WITH FLOOD PROTECTION ---
@client.on(events.NewMessage())
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        uid = event.sender_id
        now = time.time()

        # 1. Send Offline Message only once every 5 minutes
        if sleep_mode_active:
            if uid not in last_notified or (now - last_notified.get(uid, 0) > 300):
                await event.reply(OFFLINE_MSG)

        # 2. Forward message but only send the "Header" once every 60 seconds per user
        if uid not in last_notified or (now - last_notified.get(uid, 0) > 60):
            user = await event.get_sender()
            header = f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{uid}`"
            await client.send_message(config.ADMIN_ID, header)
            last_notified[uid] = now
        
        # 3. Always forward the actual content
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- 3. ADMIN REPLY ---
@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    uid, msg = int(event.pattern_match.group(1)), event.pattern_match.group(2).strip()
    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg}")
        await event.reply(f"✅ Sent to `{uid}`")
    except Exception: await event.reply("❌ Failed to send.")

# --- 4. START COMMAND & CALLBACKS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    try: database.approve_user_24h(user.id, user.username)
    except: pass
    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    welcome_text = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n"
                    f"To access today's confirmed selections, please buy a ticket below.")
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    user = await event.get_sender()
    await event.answer("✅ Sent to Admin.", alert=True)
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 5. RUNNER ---
async def main():
    try:
        database.init_db()
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT LIVE | Flood Protection Active")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__': asyncio.run(main())
