import logging
import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import UserIsBlockedError, PeerIdInvalidError, FloodWaitError
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v41', config.API_ID, config.API_HASH)

# --- 1. ADMIN COMMANDS (PRIORITY) ---

@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_handler(event):
    global sleep_mode_active
    raw = event.raw_text.lower()
    
    # BROADCAST (Flood Protected)
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
                await asyncio.sleep(0.3) 
            except FloodWaitError as e: await asyncio.sleep(e.seconds)
            except: continue
        await status_msg.edit(f"✅ **Broadcast Done**\nSent: {success}")

    elif raw.startswith('/sleep'):
        sleep_mode_active = 'on' in raw
        await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

    elif raw == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        await event.reply(f"📊 **Total Subscribers: {total}**")

# --- 2. USER COMMANDS (RESTORED WELCOME MESSAGE) ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Visitor"
    
    # Alert Admin
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`")
    
    # Save/Update User in Database
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (user.id, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()

    # RESTORED PROFESSIONAL MESSAGE
    welcome_text = (
        f"Hello 👋 {first_name}!\n\n"
        f"**Welcome to Mr. White | Official Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 **PREMIUM INFO ARRIVED**\n"
        f"⭐ **CONFIRMED TICKET** 🎫\n\n"
        f"☑ **Fixed Tips:** Correct Score\n"
        f"✔ **Verification:** 100% Guaranteed\n\n"
        f"To access today's confirmed selections, please check the price via the link below and click 'I Have Paid'."
    )
    
    buttons = [
        [Button.inline("💳 Check Price & Buy Ticket", data="pay_options")],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

# --- 3. CALLBACKS & PAYMENTS ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    
    if data == "pay_options":
        btns = [
            [Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
            [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
            [Button.inline("⬅️ Back", data="back_start")]
        ]
        await event.edit("🎯 **Select your payment method:**", buttons=btns)

    elif data == "pay_crypto":
        await event.edit("💎 **Cryptocurrency Payment**\n\nPrice: **40 USD**", 
                         buttons=[[Button.url("🔗 Pay 40 USD", "https://pay.oxapay.com/10368962")],
                                  [Button.inline("⬅️ Back", data="pay_options")]])

    elif data == "claim_pay":
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{event.sender_id}"), Button.inline("❌ Reject", data=f"rej_{event.sender_id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{event.sender_id}`", buttons=btns)

# --- 4. FORWARDING ---
@client.on(events.NewMessage())
async def handle_incoming(event):
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    if sleep_mode_active: await event.reply(OFFLINE_MSG)
    user = await event.get_sender()
    try:
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
        await client.forward_messages(config.ADMIN_ID, event.message)
    except: pass

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
