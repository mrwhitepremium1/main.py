import logging
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_v22', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. FIXED REPLY COMMAND ---
# Robust pattern to catch the ID and the full multi-line message
@client.on(events.NewMessage(pattern=r'/reply (\d+)([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    
    uid = int(event.pattern_match.group(1))
    msg = event.pattern_match.group(2).strip()
    
    if not msg:
        return await event.reply("❌ **Error:** Please provide a message after the ID.\nUsage: `/reply 12345 Hello!`")

    try:
        await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{msg}")
        await event.reply(f"✅ **Reply sent to `{uid}`**")
    except UserIsBlockedError:
        await event.reply(f"❌ **Failed:** User `{uid}` has blocked the bot.")
    except Exception as e:
        await event.reply(f"❌ **Error:** {str(e)}")

# --- 2. ADMIN: BROADCAST (FIXED FOR MULTI-LINE & MEDIA) ---
@client.on(events.NewMessage(pattern=r'^/(broadcast|boardcast)([\s\S]*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    
    # ([\s\S]*) captures ALL lines including breaks
    msg_text = event.pattern_match.group(2).strip()
    media = event.media if event.media else None

    # Fallback for media captions
    if not msg_text and event.message.message:
        msg_text = event.message.message.replace('/broadcast', '').replace('/boardcast', '').strip()

    if not msg_text and not media:
        return await event.reply("❌ **Error:** Usage: `/broadcast [Message]` or send a GIF/Photo with command in caption.")
        
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    status_msg = await event.reply(f"📣 **Broadcasting...**")
    success, blocked = 0, 0
    
    for user in users:
        try:
            if media: 
                await client.send_file(user[0], media, caption=msg_text)
            else: 
                await client.send_message(user[0], msg_text)
            success += 1
            await asyncio.sleep(0.15) 
        except (UserIsBlockedError, PeerIdInvalidError):
            blocked += 1
        except Exception: continue
        
    await status_msg.edit(f"✅ **Broadcast Done**\nSent: `{success}`\nBlocked: `{blocked}`")

# --- 3. START COMMAND (FIXED VISITOR ALERT & USER COUNT) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    uid = user.id
    username = user.username if user.username else "No Username"

    # REGISTER USER IMMEDIATELY (Prevents stuck user count)
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, last_seen) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) DO UPDATE SET last_seen = %s, username = %s
    """, (uid, username, datetime.now(), datetime.now(), username))
    conn.commit(); cur.close(); conn.close()

    # VISITOR ALERT TO ADMIN
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{uid}`\nUser: @{username}")

    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check "
                    f"the price via the link below and click **'I Have Paid'**.")
    
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 4. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 5. FORWARDING & CALLBACKS ---
@client.on(events.NewMessage())
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
        await client.forward_messages(config.ADMIN_ID, event.message)

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{user.id}`", buttons=btns)
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued for 24 hours.")
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected {uid}")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified.\nContact support for help.\n\nCommand: /support")

# --- 6. RUNNER ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
