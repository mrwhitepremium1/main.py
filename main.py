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
ONLINE_MSG = "☀️ **Mr. White is back online!**\nHow can I help you today? Feel free to check the latest tickets or message support. 🎯"
pending_replies = {} 

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v52', config.API_ID, config.API_HASH)

# --- 1. UNIFIED MESSAGE HANDLER (FIXES COMMANDS) ---
@client.on(events.NewMessage())
async def unified_handler(event):
    if not event.is_private: return
    global sleep_mode_active, pending_replies
    
    sender = await event.get_sender()
    uid = sender.id
    text = event.raw_text.strip()
    cmd = text.lower()

    # A. ADMIN LOGIC (ONLY FOR YOU)
    if uid == config.ADMIN_ID:
        # Check for Smart Reply First
        if uid in pending_replies and not text.startswith('/'):
            target_uid = pending_replies.pop(uid)
            try:
                header = "👨‍💼 **Mr. White Support:**\n\n"
                if event.media: await client.send_file(target_uid, event.media, caption=f"{header}{text}")
                else: await client.send_message(target_uid, f"{header}{text}")
                await event.reply(f"✅ **Sent to `{target_uid}`**")
            except: await event.reply("❌ Error sending message.")
            return

        # Admin Commands
        if cmd == '/users':
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT user_id, username FROM subscribers")
            users = cur.fetchall(); cur.close(); conn.close()
            user_list = f"📊 **Subscribers ({len(users)})**\n" + "━" * 15 + "\n"
            for u_id, u_name in users:
                user_list += f"🆔 `{u_id}` | @{u_name if u_name else 'None'}\n"
            await event.reply(user_list)
            return

        elif cmd.startswith('/sleep'):
            if 'off' in cmd:
                sleep_mode_active = False
                await event.reply("☀️ **Online Mode Active.**")
            else:
                sleep_mode_active = True
                await event.reply("🌙 **Sleep Mode Active.**")
            return

        elif cmd.startswith('/find'):
            match = re.search(r'\d+', text)
            if match:
                f_uid = int(match.group())
                conn = database.get_connection(); cur = conn.cursor()
                cur.execute("SELECT username FROM subscribers WHERE user_id = %s", (f_uid,))
                res = cur.fetchone(); cur.close(); conn.close()
                await event.reply(f"🔍 Result: @{res[0]}" if res else "❌ Not found.")
            return

    # B. USER LOGIC (EVERYONE ELSE)
    else:
        # Start Command
        if cmd == '/start':
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, sender.username, datetime.now(), datetime.now()))
            conn.commit(); cur.close(); conn.close()
            # Notify Admin
            btns = [[Button.inline("💬 Reply", data=f"rep_{uid}"), Button.inline("🚫 Block", data=f"blk_{uid}")]]
            await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {sender.first_name}\nID: `{uid}`", buttons=btns)
            # Welcome
            welcome = (f"Hello 👋 {sender.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                       "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫")
            await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=[
                [Button.inline("💳 Check Price", data="pay_options")], [Button.inline("✅ I Have Paid", data="claim_pay")]
            ])
            return

        elif cmd == '/status':
            status = "✅ Active" if database.is_user_approved(uid) else "❌ Inactive"
            await event.reply(f"📊 **Your Status:** {status}")
            return

        # Catch-all Support Forwarding (If not a command)
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        btns = [[Button.inline("💬 Reply", data=f"rep_{uid}"), Button.inline("🚫 Block", data=f"blk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {sender.first_name}\n🆔: `{uid}`", buttons=btns)
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- 2. CALLBACK HANDLER (BUTTONS) ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    try:
        if data.startswith('app_'):
            uid = int(data.split('_')[1])
            database.approve_user_24h(uid, "User")
            await event.edit(f"✅ Approved `{uid}`")
            await client.send_file(uid, config.TICKET_URL, caption="✅ Verified!")
        elif data.startswith('rep_'):
            uid = int(data.split('_')[1])
            pending_replies[config.ADMIN_ID] = uid
            await event.answer("✍️ Write your reply now...", alert=True)
        elif data == "pay_options":
            btns = [[Button.url("🌍 International / Mobile Money", config.SELAR_PAYMENT_LINK)],
                    [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
                    [Button.inline("⬅️ Back", data="back_start")]]
            await event.edit("🎯 **Select payment method:**", buttons=btns)
        elif data == "pay_crypto":
            await event.edit("💎 **Crypto Price: 40 USD**", buttons=[[Button.url("🔗 Pay Now", "https://pay.oxapay.com/10368962")], [Button.inline("⬅️ Back", data="pay_options")]])
        elif data == "claim_pay":
            await event.answer("✅ Claim sent.", alert=True)
            user = await event.get_sender()
            await client.send_message(config.ADMIN_ID, f"🚨 **Claim!** ID: `{user.id}`", buttons=[[Button.inline("✅ Approve", data=f"app_{user.id}")]])
    except FloodWaitError as e: await asyncio.sleep(e.seconds)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
