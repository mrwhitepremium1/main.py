import logging
import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v39', config.API_ID, config.API_HASH)

# --- 1. ADMIN COMMANDS (TOP PRIORITY) ---

@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_handler(event):
    global sleep_mode_active
    raw = event.raw_text.lower()
    
    # BROADCAST
    if raw.startswith(('/broadcast', '/boardcast')):
        msg_text = event.raw_text.split(maxsplit=1)[1] if len(event.raw_text.split()) > 1 else ""
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        status_msg = await event.reply("📣 **Broadcasting...**")
        success = 0
        for user in users:
            try:
                if event.media: await client.send_file(user[0], event.media, caption=msg_text)
                else: await client.send_message(user[0], msg_text)
                success += 1
                await asyncio.sleep(0.15)
            except: continue
        await status_msg.edit(f"✅ **Broadcast Done**\nSent: {success}")

    # SLEEP
    elif raw.startswith('/sleep'):
        sleep_mode_active = 'on' in raw
        status = "Enabled 🌙" if sleep_mode_active else "Disabled ☀️"
        await event.reply(f"**Sleep Mode {status}**")

    # FIND
    elif raw.startswith('/find'):
        match = re.search(r'\d+', raw)
        if match:
            uid = int(match.group())
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT username, last_seen FROM subscribers WHERE user_id = %s", (uid,))
            res = cur.fetchone()
            cur.close(); conn.close()
            if res:
                user_str = f"@{res[0]}" if res[0] else "@No Username"
                await event.reply(f"🔍 **User Found:**\n🆔 ID: `{uid}`\n👤 User: {user_str}\n🕒 Last Seen: {res[1]}")
            else: await event.reply("❌ User not found.")

    # USERS (Tracks your 59 subscribers)
    elif raw == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        await event.reply(f"📊 **Total Subscribers: {total}**")

# --- 2. CALLBACKS (APPROVE / REJECT / PAYMENTS) ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    
    # Admin Approval Logic
    if data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!** Access granted for 24h.")
    
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected {uid}")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified.\nPlease contact support.")

    # Payment Menu
    elif data == "pay_options":
        btns = [[Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
                [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
                [Button.inline("⬅️ Back", data="back_start")]]
        await event.edit("🎯 **Select your payment method:**", buttons=btns)

    elif data == "pay_crypto":
        await event.edit("💎 **Cryptocurrency Payment**\n\nPrice: **40 USD**", 
                         buttons=[[Button.url("🔗 Pay 40 USD", "https://pay.oxapay.com/10368962")],
                                  [Button.inline("⬅️ Back", data="pay_options")]])

# --- 3. USER COMMANDS ---

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    msg = "📊 Status: Active 🤝\n\nYour subscription is currently active." if database.is_user_approved(event.sender_id) else "📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access."
    await event.reply(msg)

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 4. FORWARDING (PLACED LAST) ---

@client.on(events.NewMessage())
async def handle_incoming(event):
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    if sleep_mode_active: await event.reply(OFFLINE_MSG)
    user = await event.get_sender()
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
    await client.forward_messages(config.ADMIN_ID, event.message)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
