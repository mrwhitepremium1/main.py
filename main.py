import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config
import database

# Use a fresh session name to clear any stuck requests
SESSION = 'mr_white_v60_final'

logging.basicConfig(level=logging.INFO)
client = TelegramClient(SESSION, config.API_ID, config.API_HASH)

# --- SETTINGS & STATE ---
pending_replies = {}
sleep_mode_active = False

# Helper function to send messages safely with a forced delay
async def safe_send(target, message=None, file=None, buttons=None, forward=None):
    try:
        if forward:
            await client.forward_messages(target, forward)
        elif file:
            await client.send_file(target, file, caption=message, buttons=buttons)
        else:
            await client.send_message(target, message, buttons=buttons)
        
        # FORCED DELAY: This is the secret to stopping the Flood Wait
        await asyncio.sleep(2.5) 
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
    except Exception as e:
        logging.error(f"Error in safe_send: {e}")

# --- 1. ADMIN HANDLER ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_handler(event):
    global sleep_mode_active, pending_replies
    text = event.raw_text.strip()
    cmd = text.lower()

    if config.ADMIN_ID in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(config.ADMIN_ID)
        await safe_send(target_uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
        await event.reply(f"✅ **Sent to `{target_uid}`**")
        return

    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM subscribers")
        users = cur.fetchall(); cur.close(); conn.close()
        msg = f"📊 **Subscribers ({len(users)})**\n" + "━" * 15 + "\n"
        for u_id, u_name in users:
            msg += f"🆔 `{u_id}` | @{u_name if u_name else 'None'}\n"
        await event.reply(msg)

    elif cmd.startswith('/sleep'):
        sleep_mode_active = 'off' not in cmd
        await event.reply(f"🛰 **Sleep Mode: {'ON' if sleep_mode_active else 'OFF'}**")

# --- 2. USER HANDLER ---
@client.on(events.NewMessage(incoming=True))
async def user_handler(event):
    if event.sender_id == config.ADMIN_ID: return
    
    sender = await event.get_sender()
    uid = event.sender_id
    text = event.raw_text.strip().lower()

    if text == '/start':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, sender.username, datetime.now(), datetime.now()))
        conn.commit(); cur.close(); conn.close()
        
        welcome = (f"Hello 👋 {sender.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                   "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫")
        
        btns = [[Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
                [Button.url("💰 Crypto (USDT)", "https://pay.oxapay.com/10368962")],
                [Button.inline("✅ I Have Paid", data="claim_pay")]]
        
        await safe_send(uid, welcome, file=config.COVERED_TICKET_URL, buttons=btns)
        
        # Admin Alert
        admin_btns = [[Button.inline("💬 Reply", data=f"rep_{uid}")]]
        await safe_send(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {sender.first_name}\nID: `{uid}`", buttons=admin_btns)
    else:
        if sleep_mode_active:
            await safe_send(uid, "🌙 **Mr. White is offline. Message saved.**")
        
        await safe_send(config.ADMIN_ID, f"📩 **MSG FROM `{uid}`**")
        await safe_send(config.ADMIN_ID, forward=event.message)

# --- 3. CALLBACK HANDLER ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data.startswith('rep_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Write your reply now...", alert=True)
    elif data == "claim_pay":
        await event.answer("✅ Claim sent.", alert=True)
        user = await event.get_sender()
        await safe_send(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM**\nUser: {user.first_name}\nID: `{user.id}`")

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        print("✅ Bot v60 Started. Anti-Flood Delay Active.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"🛑 Wait {e.seconds}s")

if __name__ == '__main__':
    asyncio.run(main())
