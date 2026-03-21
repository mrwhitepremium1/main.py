import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v70_final', config.API_ID, config.API_HASH)
pending_replies = {}
sleep_mode_active = False

# --- 1. ADMIN LOGIC (COMMANDS & QUICK REPLIES) ---

@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_main_handler(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    cmd = text.lower()

    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        return await event.reply(f"📊 **Total Subscribers:** {total}")

    elif cmd.startswith('/sleep'):
        sleep_mode_active = ("on" in cmd)
        return await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

    elif cmd.startswith('/broadcast'):
        msg_text = text[10:].strip()
        media = await event.get_reply_message() if event.is_reply else None
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        
        status_msg = await event.reply(f"🚀 **Broadcasting...**")
        success = 0
        for u in users:
            try:
                if media and media.media: await client.send_file(u[0], media.media, caption=msg_text)
                else: await client.send_message(u[0], msg_text)
                success += 1
                await asyncio.sleep(0.3)
            except: continue
        return await status_msg.edit(f"✅ **Broadcast Done.** Sent: {success}")

    # Handle Quick Reply (if not a command)
    if event.sender_id in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(event.sender_id)
        try:
            await client.send_message(target_uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except: await event.reply("❌ User blocked the bot.")

# --- 2. USER LOGIC (PROFESSIONAL MESSAGES) ---

@client.on(events.NewMessage(pattern='/start', incoming=True))
async def start_handler(event):
    if event.sender_id == config.ADMIN_ID: return
    user = await event.get_sender()
    uid = user.id
    
    database.init_db() # Ensures table exists
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()

    # Professional Visitor Alert
    admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
    alert = (f"👤 **New Visitor Alert!**\n━━━━━━━━━━━━━━━━━━━━\n"
             f"**Name:** {user.first_name}\n**ID:** `{uid}`\n"
             f"**User:** @{user.username if user.username else 'None'}")
    await client.send_message(config.ADMIN_ID, alert, buttons=admin_btns)

    # Professional Welcome (Africa renamed to Pay Via Selar)
    welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
               "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
    btns = [[Button.url("🌍 Pay Via Selar", config.SELAR_PAYMENT_LINK)],
            [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)

@client.on(events.NewMessage(pattern='/support', incoming=True))
async def support_handler(event):
    await event.reply("💬 **Connected to Support.**\nExplain your issue clearly or send your receipt; Mr. White is listening. 🎯")

# --- 3. CALLBACK HANDLERS (APPROVE/REJECT) ---

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
        
        approve_msg = ("✅ **PAYMENT VERIFIED**\n━━━━━━━━━━━━━━━━━━━━\n"
                       "🎫 **YOUR OFFICIAL TICKET HAS BEEN ISSUED**\n\n"
                       "Your access is now active for **24 Hours**. Please find your confirmed selections on the ticket above.\n\n"
                       "🤝 **Good Luck & Stay Disciplined.**")
        
        await event.edit(f"✅ **Approved `{uid}`**")
        await client.send_file(uid, config.TICKET_URL, caption=approve_msg)

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        reject_msg = ("❌ **Payment Rejected**\n\nWe could not verify your payment.\n\n"
                      "If you have already made a payment, kindly contact support immediately "
                      "with your proof of payment (screenshot or transaction ID) for manual confirmation.\n\n"
                      "**Support:** /support")
        
        await event.edit(f"❌ **Rejected `{uid}`**")
        await client.send_message(uid, reject_msg)

    elif data.startswith('qr_'):
        uid = int(data.split('_')[1]); pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
