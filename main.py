import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
import config, database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v75', config.API_ID, config.API_HASH)
pending_replies = {}
sleep_mode_active = False

# --- 1. CORE COMMANDS (START, STATUS, SUPPORT) ---
@client.on(events.NewMessage(pattern=r'^/(start|status|support)'))
async def core_commands(event):
    cmd = event.pattern_match.group(1).lower()
    uid, user = event.sender_id, await event.get_sender()
    first_name = user.first_name or "User"

    if cmd == 'start':
        database.init_db()
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s, username = %s", (uid, user.username, datetime.now(), datetime.now(), user.username))
        conn.commit(); cur.close(); conn.close()

        welcome = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                   "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
                   "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
        btns = [[Button.url("🌍 Pay Via Selar", config.SELAR_PAYMENT_LINK)],
                [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
                [Button.inline("✅ I Have Paid", data="claim_pay")]]
        await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)

        if uid != config.ADMIN_ID:
            adm_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"blk_{uid}")]]
            alert = (f"👤 **New Visitor Alert!**\n━━━━━━━━━━━━━━━━━━━━\n**Name:** {first_name}\n**ID:** `{uid}`\n**User:** @{user.username}")
            await client.send_message(config.ADMIN_ID, alert, buttons=adm_btns)

    elif cmd == 'status':
        is_active = database.is_user_approved(uid)
        await event.reply("📊 Status: **Active** ✅" if is_active else "📊 Status: **Inactive** ❌")

    elif cmd == 'support':
        await event.reply("💬 **Connected to Support.**\nExplain your issue clearly; Mr. White is listening. 🎯")

# --- 2. ADMIN SUITE (FIXED MEDIA REPLIES) ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_suite(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    
    if text.startswith('/'):
        if text.lower() == '/users':
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
            cur.close(); conn.close(); await event.reply(f"📊 **Total Subscribers:** {total}")
        elif text.lower().startswith('/sleep'):
            sleep_mode_active = ("on" in text.lower())
            await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")
        elif text.lower().startswith('/broadcast'):
            msg = text[10:].strip(); media = await event.get_reply_message() if event.is_reply else None
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall(); cur.close(); conn.close()
            for u in users:
                try:
                    if media: await client.send_file(u[0], media.media, caption=msg)
                    else: await client.send_message(u[0], msg)
                    await asyncio.sleep(0.3)
                except: continue
            await event.reply("✅ **Broadcast Done.**")
        return

    if event.sender_id in pending_replies:
        uid = pending_replies.pop(event.sender_id)
        try:
            prefix = "👨‍💼 **Mr. White Support:**\n\n"
            if event.media: await client.send_file(uid, event.media, caption=f"{prefix}{text}" if text else prefix)
            else: await client.send_message(uid, f"{prefix}{text}")
            await event.reply(f"✅ **Replied to `{uid}`**")
        except: await event.reply("❌ Failed. User blocked the bot.")

# --- 3. SUPPORT FORWARDER ---
@client.on(events.NewMessage(incoming=True))
async def support_forwarder(event):
    if event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/') or not event.is_private: return
    user = await event.get_sender()
    btns = [[Button.inline("💬 Reply", data=f"qr_{user.id}"), Button.inline("🚫 Block", data=f"blk_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT FROM `{user.id}`**", buttons=btns)
    await client.forward_messages(config.ADMIN_ID, event.message)

# --- 4. CALLBACKS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()

    if data == "claim_pay":
        user = await event.get_sender()
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM!**\nID: `{user.id}`", buttons=btns)
        await event.answer("✅ Sent to Admin.", alert=True)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1]); database.approve_user_24h(uid)
        msg = ("✅ **PAYMENT VERIFIED**\n━━━━━━━━━━━━━━━━━━━━\n🎫 **YOUR OFFICIAL TICKET HAS BEEN ISSUED**\n\n"
               "Your access is now active for **24 Hours**. Please find selections on the ticket above.\n\n🤝 **Good Luck.**")
        await client.send_file(uid, config.TICKET_URL, caption=msg)
        await event.edit(f"✅ **Approved `{uid}`**")

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        rej = ("❌ **Payment Rejected**\n\nWe could not verify your payment.\n\n"
               "If you have already made a payment, kindly contact support immediately with your proof of payment.\n\n**Support:** /support")
        await client.send_message(uid, rej); await event.edit(f"❌ **Rejected `{uid}`**")

    elif data.startswith('blk_'):
        uid = int(data.split('_')[1]); conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,)); conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 **User `{uid}` Deleted.**")

    elif data.startswith('qr_'):
        pending_replies[config.ADMIN_ID] = int(data.split('_')[1]); await event.answer("✍️ Send reply (Text/Media)...", alert=True)

async def main():
    database.init_db(); await client.start(bot_token=config.BOT_TOKEN); await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
