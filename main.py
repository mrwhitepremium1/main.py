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
client = TelegramClient('mr_white_v53', config.API_ID, config.API_HASH)

# --- 1. THE ONLY MESSAGE HANDLER (CRITICAL FOR COMMANDS) ---
@client.on(events.NewMessage(incoming=True)) # incoming=True prevents the bot from catching its own messages
async def global_message_handler(event):
    if not event.is_private: return
    global sleep_mode_active, pending_replies
    
    sender = await event.get_sender()
    if not sender: return
    uid = sender.id
    text = event.raw_text.strip()
    cmd = text.lower()

    # --- A. ADMIN SECTION (YOU ONLY) ---
    if uid == config.ADMIN_ID:
        # 1. Handle Active Support Replies
        if uid in pending_replies and not text.startswith('/'):
            target_uid = pending_replies.pop(uid)
            try:
                header = "👨‍💼 **Mr. White Support:**\n\n"
                if event.media: await client.send_file(target_uid, event.media, caption=f"{header}{text}")
                else: await client.send_message(target_uid, f"{header}{text}")
                await event.reply(f"✅ **Sent to `{target_uid}`**")
            except Exception as e: await event.reply(f"❌ Failed: {str(e)}")
            return

        # 2. Admin Commands
        if cmd == '/users':
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT user_id, username FROM subscribers")
            users = cur.fetchall(); cur.close(); conn.close()
            msg = f"📊 **Subscribers ({len(users)})**\n" + "━" * 15 + "\n"
            for u_id, u_name in users:
                msg += f"🆔 `{u_id}` | @{u_name if u_name else 'None'}\n"
            await event.reply(msg)
            return

        elif cmd.startswith('/sleep'):
            if 'off' in cmd:
                sleep_mode_active = False
                await event.reply("☀️ **Sleep Mode: OFF. You are now ONLINE.**")
            else:
                sleep_mode_active = True
                await event.reply("🌙 **Sleep Mode: ON. Offline message active.**")
            return

        elif cmd.startswith('/find'):
            match = re.search(r'\d+', text)
            if match:
                target = int(match.group())
                conn = database.get_connection(); cur = conn.cursor()
                cur.execute("SELECT username FROM subscribers WHERE user_id = %s", (target,))
                res = cur.fetchone(); cur.close(); conn.close()
                await event.reply(f"🔍 Result: @{res[0]}" if res else "❌ Not found in DB.")
            return

    # --- B. USER SECTION (EVERYONE ELSE) ---
    else:
        # 1. Start Command
        if cmd == '/start':
            # Save to Database
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s, username = %s", (uid, sender.username, datetime.now(), datetime.now(), sender.username))
            conn.commit(); cur.close(); conn.close()
            
            # Welcome Message
            welcome = (f"Hello 👋 {sender.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                       "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫")
            await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=[
                [Button.inline("💳 Check Price", data="pay_options")], [Button.inline("✅ I Have Paid", data="claim_pay")]
            ])
            
            # Alert Admin
            btns = [[Button.inline("💬 Reply", data=f"rep_{uid}"), Button.inline("🚫 Block", data=f"blk_{uid}")]]
            await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {sender.first_name}\nID: `{uid}`", buttons=btns)
            return

        # 2. Status Command
        elif cmd == '/status':
            status = "✅ Active" if database.is_user_approved(uid) else "❌ Inactive"
            await event.reply(f"📊 **Status:** {status}")
            return

        # 3. Support Message (Forwarding)
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        
        # Forward to Admin with Action Buttons
        btns = [[Button.inline("💬 Reply", data=f"rep_{uid}"), Button.inline("🚫 Block", data=f"blk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {sender.first_name}\n🆔: `{uid}`", buttons=btns)
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- 2. CALLBACK HANDLER (STAYS SEPARATE) ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    try:
        if data.startswith('app_'):
            uid = int(data.split('_')[1])
            database.approve_user_24h(uid, "User")
            await event.edit(f"✅ Approved `{uid}`")
            await client.send_file(uid, config.TICKET_URL, caption="✅ Payment Verified!")
        elif data.startswith('rep_'):
            uid = int(data.split('_')[1])
            pending_replies[config.ADMIN_ID] = uid
            await event.answer("✍️ Write your reply now...", alert=True)
        elif data == "pay_options":
            btns = [[Button.url("🌍 International / Mobile Money", config.SELAR_PAYMENT_LINK)],
                    [Button.inline("💰 Crypto (USDT)", data="pay_crypto")]]
            await event.edit("🎯 **Select payment method:**", buttons=btns)
        elif data == "pay_crypto":
            await event.edit("💎 **Price: 40 USD**", buttons=[[Button.url("🔗 Pay Now", "https://pay.oxapay.com/10368962")]])
    except FloodWaitError as e: await asyncio.sleep(e.seconds)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    print("Bot is running...")
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
