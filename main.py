import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
import config, database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_vision', config.API_ID, config.API_HASH)
pending_replies = {}
sleep_mode_active = False

# --- ADMIN COMMANDS ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_handler(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    
    if text.lower() == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        return await event.reply(f"📊 **Total Subscribers:** {total}")

    elif text.lower().startswith('/sleep'):
        sleep_mode_active = ("on" in text.lower())
        return await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

    elif text.lower().startswith('/broadcast'):
        msg = text[10:].strip()
        media = await event.get_reply_message() if event.is_reply else None
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        for u in users:
            try:
                if media: await client.send_file(u[0], media.media, caption=msg)
                else: await client.send_message(u[0], msg)
                await asyncio.sleep(0.3)
            except: continue
        return await event.reply("✅ **Broadcast Done.**")

    if event.sender_id in pending_replies and not text.startswith('/'):
        uid = pending_replies.pop(event.sender_id)
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
        await event.reply(f"✅ **Sent to `{uid}`**")

# --- USER FLOW & BUTTONS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id == config.ADMIN_ID: return
    user = await event.get_sender()
    # Professional Visitor Alert
    btns = [[Button.inline("💬 Reply", data=f"qr_{user.id}"), Button.inline("🚫 Block", data=f"blk_{user.id}")]]
    alert = (f"👤 **New Visitor Alert!**\n━━━━━━━━━━━━━━━━━━━━\n"
             f"**Name:** {user.first_name}\n**ID:** `{user.id}`\n**User:** @{user.username}")
    await client.send_message(config.ADMIN_ID, alert, buttons=btns)
    
    # Welcome Message
    welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
               "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
    pay_btns = [[Button.url("🌍 Pay Via Selar", config.SELAR_PAYMENT_LINK)],
                [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
                [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await client.send_file(user.id, config.COVERED_TICKET_URL, caption=welcome, buttons=pay_btns)

@client.on(events.CallbackQuery())
async def callbacks(event):
    data = event.data.decode()
    if data.startswith('blk_'): # Instant Block Fix
        uid = int(data.split('_')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 **User `{uid}` Blocked.**")
    elif data.startswith('app_'): # Professional Approve
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid)
        msg = ("✅ **PAYMENT VERIFIED**\n━━━━━━━━━━━━━━━━━━━━\n"
               "🎫 **YOUR OFFICIAL TICKET HAS BEEN ISSUED**\n\n"
               "Your access is active for **24 Hours**. Find selections on the ticket above.")
        await event.edit(f"✅ **Approved `{uid}`**")
        await client.send_file(uid, config.TICKET_URL, caption=msg)
    elif data == "claim_pay":
        user = await event.get_sender()
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM!**\nID: `{user.id}`", buttons=btns)
    elif data.startswith('qr_'):
        pending_replies[config.ADMIN_ID] = int(data.split('_')[1])
        await event.answer("✍️ Type reply now...")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
