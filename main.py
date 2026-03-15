import logging
import os
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v6_final', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. START COMMAND (Clean Menu) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    try:
        database.approve_user_24h(user.id, user.username)
    except: pass

    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check "
                    f"the price via the link below and click **'I Have Paid'**.")
    
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 2. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 3. FORWARD MESSAGES TO ADMIN ---
@client.on(events.NewMessage())
async def forward_to_admin(event):
    # Only forward private messages that aren't commands and aren't from the Admin
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        user = await event.get_sender()
        header = f"📩 **NEW SUPPORT MESSAGE**\n👤 From: {user.first_name}\n🆔 ID: `{user.id}`"
        await client.send_message(config.ADMIN_ID, header)
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- 4. ADMIN REPLY SYSTEM ---
# Usage: /reply [User_ID] [Your Message]
@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    user_id = int(event.pattern_match.group(1))
    reply_msg = event.pattern_match.group(2).strip()
    
    try:
        await client.send_message(user_id, f"👨‍💼 **Mr. White Support:**\n\n{reply_msg}")
        await event.reply(f"✅ Reply sent to `{user_id}`")
    except Exception:
        await event.reply("❌ Error: Could not send message. The user might have blocked the bot.")

# --- 5. BROADCAST & CALLBACKS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "claim_pay":
        await event.answer("✅ Sent to Admin.", alert=True)
        user = await event.get_sender()
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ Approved User {uid}")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour ticket has been issued for 24 hours.")
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected User {uid}")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified at this time.\nPlease contact Mr White for assistance.\n\nCommand: /support")

# --- 6. RUNNER ---
async def main():
    try:
        database.init_db()
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT IS FULLY REPAIRED & FORWARDING ACTIVE!")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
