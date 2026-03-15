import logging
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- INITIAL STATE ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_v12', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. ADMIN MANAGEMENT COMMANDS ---
@client.on(events.NewMessage(pattern=r'/sleep (on|off)'))
async def toggle_sleep(event):
    global sleep_mode_active
    if event.sender_id != config.ADMIN_ID: return
    choice = event.pattern_match.group(1).lower()
    sleep_mode_active = (choice == "on")
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
        uname = f"@{r[1]}" if r[1] else "No Username"
        last_active = r[2].strftime("%Y-%m-%d %H:%M") if r[2] else "Unknown"
        response += f"• `{r[0]}` | {uname}\n  └ 🕒 {last_active}\n"
    await event.reply(response)

# NEW: Search by User ID
@client.on(events.NewMessage(pattern=r'/find (\d+)'))
async def find_user(event):
    if event.sender_id != config.ADMIN_ID: return
    search_id = int(event.pattern_match.group(1))
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id, username, last_seen, approved FROM subscribers WHERE user_id = %s", (search_id,))
    user = cur.fetchone()
    cur.close(); conn.close()
    
    if user:
        status = "✅ ACTIVE" if user[3] else "❌ INACTIVE"
        uname = f"@{user[1]}" if user[1] else "No Username"
        last_active = user[2].strftime("%Y-%m-%d %H:%M") if user[2] else "Never"
        msg = (f"🔍 **User Found:**\n\n🆔 ID: `{user[0]}`\n👤 Username: {uname}\n"
               f"🕒 Last Seen: `{last_active}`\n📊 Status: {status}")
        await event.reply(msg)
    else:
        await event.reply(f"❌ No user found with ID `{search_id}`")

# --- 2. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    try:
        database.approve_user_24h(user.id, user.username)
    except: pass

    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check "
                    f"the price via the link below and click **'I Have Paid'**.")
    
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 4. FORWARDING & REPLY ---
@client.on(events.NewMessage())
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
        await client.forward_messages(config.ADMIN_ID, event.message)

@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    uid, msg = int(event.pattern_match.group(1)), event.pattern_match.group(2).strip()
    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg}")
        await event.reply(f"✅ Sent to `{uid}`")
    except: await event.reply("❌ User blocked bot.")

# --- 5. CALLBACKS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued for 24 hours.")
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected {uid}")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified.\nContact support for help.\n\nCommand: /support")

# --- 6. RUNNER ---
async def main():
    try:
        database.init_db()
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT READY | /find [id] to search, /users to list")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__': asyncio.run(main())
