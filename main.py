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
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v32', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. ADMIN COMMANDS (PRIORITY) ---

@client.on(events.NewMessage(pattern=r'^/reply\s+(\d+)\s+([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    uid = int(event.pattern_match.group(1))
    msg_content = event.pattern_match.group(2).strip()
    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg_content}")
        await event.reply(f"✅ **Reply sent to `{uid}`**")
    except Exception as e:
        await event.reply(f"❌ **Error:** {str(e)}")

# NEW: BLOCK COMMAND
@client.on(events.NewMessage(pattern=r'/block (\d+)'))
async def block_user(event):
    if event.sender_id != config.ADMIN_ID: return
    uid = int(event.pattern_match.group(1))
    conn = database.get_connection(); cur = conn.cursor()
    # Check if user exists
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (uid,))
    if cur.fetchone():
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit()
        await event.reply(f"🚫 **User `{uid}` has been blocked and removed from the database.**")
    else:
        await event.reply("❌ User ID not found in database.")
    cur.close(); conn.close()

@client.on(events.NewMessage(pattern=r'^/(broadcast|boardcast)([\s\S]*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(2).strip()
    media = event.media if event.media else None
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    status_msg = await event.reply(f"📣 **Broadcasting...**")
    success, blocked_count = 0, 0
    for user in users:
        try:
            if media: await client.send_file(user[0], media, caption=msg_text)
            else: await client.send_message(user[0], msg_text)
            success += 1
            await asyncio.sleep(0.15) 
        except (UserIsBlockedError, PeerIdInvalidError):
            blocked_count += 1
        except Exception: continue
    await status_msg.edit(f"✅ **Broadcast Done**\nSent: {success}\nBlocked: {blocked_count}")

@client.on(events.NewMessage(pattern=r'/sleep (on|off)'))
async def toggle_sleep(event):
    global sleep_mode_active
    if event.sender_id != config.ADMIN_ID: return
    sleep_mode_active = (event.pattern_match.group(1).lower() == "on")
    status = "Enabled 🌙" if sleep_mode_active else "Disabled ☀️"
    await event.reply(f"**Sleep Mode {status}**")

@client.on(events.NewMessage(pattern=r'/find (\d+)'))
async def find_user(event):
    if event.sender_id != config.ADMIN_ID: return
    uid = int(event.pattern_match.group(1))
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT username, last_seen FROM subscribers WHERE user_id = %s", (uid,))
    res = cur.fetchone()
    cur.close(); conn.close()
    if res:
        user_str = f"@{res[0]}" if res[0] else "@No Username"
        await event.reply(f"🔍 **User Found:**\n🆔 ID: `{uid}`\n👤 User: {user_str}\n🕒 Last Seen: {res[1]}")
    else:
        await event.reply("❌ User not found.")

@client.on(events.NewMessage(pattern='/users'))
async def list_users(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Total Subscribers:** {total}")

# --- 2. USER COMMANDS ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    uid = user.id
    first_name = user.first_name if user.first_name else "No Name"
    username = f"@{user.username}" if user.username else "@No Username"
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s, username = %s", (uid, user.username, datetime.now(), datetime.now(), user.username))
    conn.commit(); cur.close(); conn.close()
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{uid}`\nUser: {username}")
    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]]
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check the price via the link below and click 'I Have Paid'.")
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 3. FORWARDING (PLACED LAST) ---

@client.on(events.NewMessage())
async def handle_incoming(event):
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID:
        return
    if sleep_mode_active:
        await event.reply(OFFLINE_MSG)
    user = await event.get_sender()
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
    await client.forward_messages(config.ADMIN_ID, event.message)

# --- 4. CALLBACKS ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{user.id}`", buttons=btns)
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued for 24 hours.")
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected {uid}")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified.\nPlease contact support.")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
