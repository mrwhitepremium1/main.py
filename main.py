import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received. 🎯"
pending_replies = {}

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v67', config.API_ID, config.API_HASH)

# --- 1. ADMIN LOGIC (COMMANDS & REPLIES) ---

@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_handler(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    cmd = text.lower()

    # Quick Reply Handler
    if event.sender_id in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(event.sender_id)
        try:
            await client.send_message(target_uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except: await event.reply("❌ **Failed.** User blocked the bot.")
        return

    # Standard Commands
    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        await event.reply(f"📊 **Total Subscribers:** {total}")

    elif cmd.startswith('/sleep'):
        sleep_mode_active = ("on" in cmd)
        await event.reply(f"🌙 Sleep Mode: {'Enabled' if sleep_mode_active else 'Disabled'}")

# --- 2. USER COMMANDS ---

@client.on(events.NewMessage(pattern='/start', incoming=True))
async def start(event):
    if event.sender_id == config.ADMIN_ID: return
    user = await event.get_sender()
    uid, first_name = user.id, user.first_name or "User"
    
    # DB Update
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()
    
    # Welcome UI
    welcome = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
               "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
    
    btns = [[Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)
    
    # Admin Alert with Reply/Block
    adm_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {first_name}\nID: `{uid}`", buttons=adm_btns)

@client.on(events.NewMessage(pattern='/status', incoming=True))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: **Active** ✅\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: **Inactive** ❌\nPlease purchase a ticket to activate access.")

# --- 3. FORWARDING & CALLBACKS ---

@client.on(events.NewMessage(incoming=True))
async def support_forward(event):
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    if sleep_mode_active: await event.reply(OFFLINE_MSG)
    
    user = await event.get_sender()
    adm_btns = [[Button.inline("💬 Reply", data=f"qr_{user.id}"), Button.inline("🚫 Block", data=f"preblk_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"📩 **MSG FROM `{user.id}`**", buttons=adm_btns)
    await client.forward_messages(config.ADMIN_ID, event.message)

@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    
    if data.startswith('qr_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)

    elif data.startswith('preblk_'):
        uid = int(data.split('_')[1])
        await event.edit(f"⚠️ **Block `{uid}`?**", buttons=[[Button.inline("✅ YES", data=f"confblk_{uid}"), Button.inline("❌ NO", data="cancel")]])

    elif data.startswith('confblk_'):
        uid = int(data.split('_')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 **User `{uid}` Blocked.**")

    elif data == "cancel": await event.edit("✅ Action Cancelled.")

    elif data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("💬 Reply", data=f"qr_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM!**\nID: `{user.id}`", buttons=btns)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Verified**\nTicket issued for 24h.")

async def main():
    database.init_db() # This now handles the ALTER TABLE logic we discussed
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
