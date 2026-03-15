import logging
import os
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# Setup
logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_prod_v3', config.API_ID, config.API_HASH, connection_retries=None)

# --- 1. START COMMAND (No Guarantee/Terms Buttons) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    # Database Tracking
    database.approve_user(user.id, user.username)
    
    # Menu with ONLY Payment and "I Have Paid"
    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = (
        f"Hello 👋 {first_name}!\n\n"
        f"**Welcome to Mr. White | Official Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 **PREMIUM INFO ARRIVED**\n"
        f"⭐ **CONFIRMED TICKET** 🎫\n\n"
        f"☑ **Fixed Tips:** Correct Score\n"
        f"✔ **Verification:** 100% Guaranteed\n\n"
        f"To access today's confirmed selections, please check "
        f"the price via the link below and click **'I Have Paid'**."
    )
    
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 2. STATUS & SUPPORT (EXACT TEXT & BOLD) ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.respond("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.respond("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    # Bold text as requested
    await event.respond("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 3. CALLBACKS (I HAVE PAID / APPROVAL) ---
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
        try:
            await client.send_message(uid, "🎊 **Great news!** Your payment has been verified. Your subscription is now **ACTIVE** ✅.")
        except: pass

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected User {uid}")
        try:
            await client.send_message(uid, "❌ **Payment Claim Rejected**\nPlease contact Mr White for assistance.")
        except: pass

# --- 4. BROADCAST ---
@client.on(events.NewMessage(pattern=r'/broadcast (.*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(1)
    users = database.get_all_users()
    await event.respond(f"🚀 Sending to {len(users)} users...")
    for uid in users:
        try:
            await client.send_message(uid, msg_text)
            await asyncio.sleep(0.3)
        except: pass
    await event.respond("✅ Broadcast complete!")

# --- 5. RUN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 BOT IS LIVE!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
