import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# Use a fresh session name to clear any stuck states
SESSION = 'mr_white_v66_stable'

logging.basicConfig(level=logging.INFO)
client = TelegramClient(SESSION, config.API_ID, config.API_HASH)

# --- STATE ---
pending_replies = {}

# --- ADMIN GATEKEEPER ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_handler(event):
    global pending_replies
    text = event.raw_text.strip()
    
    # Quick Reply Logic
    if event.sender_id in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(event.sender_id)
        try:
            await client.send_message(target_uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except: await event.reply("❌ **Failed.** User might have blocked the bot.")
        return

    # Admin Commands
    cmd = text.lower()
    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        await event.reply(f"📊 **Total Subscribers:** {total}")

# --- USER HANDLER (RE-ACTIVATED) ---
@client.on(events.NewMessage(incoming=True))
async def user_handler(event):
    # CRITICAL: This line stops the bot from ignoring itself or looping
    if event.sender_id == config.ADMIN_ID: return 
    if not event.is_private: return

    uid = event.sender_id
    text = event.raw_text.strip().lower()

    # THE WELCOME MESSAGE LOGIC
    if text == '/start':
        sender = await event.get_sender()
        
        # Save to DB
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, sender.username, datetime.now(), datetime.now()))
        conn.commit(); cur.close(); conn.close()
        
        # Welcome Content
        welcome_text = (
            f"Hello 👋 {sender.first_name}!\n\n"
            "**Welcome to Mr. White | Official Bot**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💎 **PREMIUM INFO ARRIVED**\n"
            "⭐ **CONFIRMED TICKET** 🎫\n\n"
            "✅ **Fixed Tips:** Correct Score\n"
            "⚡ **Verification:** 100% Guaranteed"
        )
        
        btns = [
            [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]
        ]
        
        # Send Welcome File (Video/GIF/Photo)
        await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome_text, buttons=btns)
        
        # Notify Admin with Quick Controls
        admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {sender.first_name}\nID: `{uid}`", buttons=admin_btns)
    
    elif not text.startswith('/'):
        # Forward Support Messages
        admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"📩 **MESSAGE FROM `{uid}`**", buttons=admin_btns)
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- CALLBACKS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data.startswith('qr_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)
    elif data.startswith('preblk_'):
        uid = int(data.split('_')[1])
        await event.edit(f"⚠️ **Block `{uid}`?**", buttons=[[Button.inline("✅ YES", data=f"c_{uid}"), Button.inline("❌ NO", data="cancel")]])
    elif data.startswith('c_'):
        uid = int(data.split('_')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 User `{uid}` Blocked.")

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        print("✅ Mr. White v66 Online. Your Welcome Message is active.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"🛑 Telegram Lock: Wait {e.seconds}s")

if __name__ == '__main__': asyncio.run(main())
