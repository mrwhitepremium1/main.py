import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v69_final', config.API_ID, config.API_HASH)
pending_replies = {}
sleep_mode_active = False
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed shortly. 🎯"

# --- 1. ADMIN COMMANDS (FIXED FILTERS) ---

@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_main_handler(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    cmd = text.lower()

    # 1. Handle Commands First
    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        return await event.reply(f"📊 **Total Subscribers:** {total}")

    elif cmd.startswith('/sleep'):
        sleep_mode_active = ("on" in cmd)
        status = "Enabled 🌙" if sleep_mode_active else "Disabled ☀️"
        return await event.reply(f"**Sleep Mode {status}**")

    elif cmd.startswith('/broadcast'):
        msg_text = text[10:].strip()
        media = await event.get_reply_message() if event.is_reply else None
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        
        status_msg = await event.reply(f"🚀 **Broadcasting to {len(users)} users...**")
        success = 0
        for u in users:
            try:
                if media and media.media: await client.send_file(u[0], media.media, caption=msg_text)
                else: await client.send_message(u[0], msg_text)
                success += 1
                await asyncio.sleep(0.3)
            except: continue
        return await status_msg.edit(f"✅ **Broadcast Done.** Sent: {success}")

    # 2. Handle Quick Reply (Only if NOT a command)
    if event.sender_id in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(event.sender_id)
        try:
            await client.send_message(target_uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except: await event.reply("❌ User blocked the bot.")

# --- 2. USER HANDLERS (PROFESSIONAL MESSAGES) ---

@client.on(events.NewMessage(pattern='/start', incoming=True))
async def start_handler(event):
    if event.sender_id == config.ADMIN_ID: return
    user = await event.get_sender()
    uid = user.id
    
    # DB Update
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()

    # Professional Visitor Alert (Restored)
    admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
    alert = (f"👤 **New Visitor Alert!**\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"**Name:** {user.first_name}\n"
             f"**ID:** `{uid}`\n"
             f"**User:** @{user.username if user.username else 'None'}")
    await client.send_message(config.ADMIN_ID, alert, buttons=admin_btns)

    # Professional Welcome (Restored)
    welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
               "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
    btns = [[Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
            [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)

@client.on(events.NewMessage(pattern='/support', incoming=True))
async def support_handler(event):
    await event.reply("💬 **Connected to Support.**\nExplain your issue clearly or send your receipt; Mr. White is listening. 🎯")

# --- 3. CALLBACKS (REJECTION & UNCOVERED TICKET) ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM!**\nID: `{user.id}`", buttons=btns)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid)
        await event.edit(f"✅ **Approved `{uid}`**")
        # RESTORED: Sends the ACTUAL Uncovered Ticket
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Verified**\nYour ticket has been issued for 24h.")

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ **Rejected `{uid}`**")
        await client.send_message(uid, "❌ **Payment Rejected**\nCould not verify. Contact support.")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
