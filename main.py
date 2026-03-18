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
client = TelegramClient('mr_white_master_v48', config.API_ID, config.API_HASH)

# --- 1. CALLBACK HANDLER ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    
    # ADMIN ACTIONS
    if data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ **Approved `{uid}`**")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!**\nAccess granted for 24h.")
    
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ **Rejected `{uid}`**")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nYour payment could not be verified.")

    elif data.startswith('rep_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)

    elif data.startswith('blk_'):
        uid = int(data.split('_')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🚫 **User `{uid}` Blocked**")

    # UPDATED USER ACTIONS (INTERNATIONAL SUPPORT)
    elif data == "pay_options":
        # Updated Label to reflect global currency support (USD, GBP, GHS, ZAR, etc.)
        btns = [[Button.url("🌍 International / Mobile Money", config.SELAR_PAYMENT_LINK)],
                [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
                [Button.inline("⬅️ Back", data="back_start")]]
        await event.edit("🎯 **Select your preferred payment method:**", buttons=btns)

    elif data == "pay_crypto":
        # Linked to your 40 USD invoice
        await event.edit("💎 **Cryptocurrency Payment**\n\nPrice: **40 USD**", 
                         buttons=[[Button.url("🔗 Pay 40 USD", "https://pay.oxapay.com/10368962")],
                                  [Button.inline("⬅️ Back", data="pay_options")]])

    elif data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{user.id}`", buttons=btns)

# --- 2. ADMIN INTERFACE ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_interface(event):
    global sleep_mode_active, pending_replies
    text = event.raw_text.strip().lower()

    if config.ADMIN_ID in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(config.ADMIN_ID)
        try:
            header = "👨‍💼 **Mr. White Support:**\n\n"
            if event.media: await client.send_file(target_uid, event.media, caption=f"{header}{event.raw_text}")
            else: await client.send_message(target_uid, f"{header}{event.raw_text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except: await event.reply("❌ Failed to send.")
        return

    if text.startswith('/sleep'):
        if 'off' in text:
            sleep_mode_active = False
            await event.reply("☀️ **Online Mode. Notifying subscribers...**")
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall(); cur.close(); conn.close()
            for u in users:
                try:
                    await client.send_message(u[0], ONLINE_MSG)
                    await asyncio.sleep(0.3)
                except FloodWaitError as e: await asyncio.sleep(e.seconds)
                except: continue
        else:
            sleep_mode_active = True
            await event.reply("🌙 **Sleep Mode Enabled.**")

    elif text == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]; cur.close(); conn.close()
        await event.reply(f"📊 **Total Subscribers: {total}**")

# --- 3. MAIN HANDLER ---
@client.on(events.NewMessage())
async def main_handler(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID: return
    
    text = event.raw_text.strip()
    
    if text == '/start':
        user = await event.get_sender()
        btns = [[Button.inline("💬 Reply", data=f"rep_{user.id}"), Button.inline("🚫 Block", data=f"blk_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {user.first_name}\nID: `{user.id}`", buttons=btns)
        welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                   "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫")
        await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome, buttons=[
            [Button.inline("💳 Check Price & Buy Ticket", data="pay_options")], [Button.inline("✅ I Have Paid", data="claim_pay")]
        ])

    elif text == '/status':
        msg = "📊 Status: Active 🤝" if database.is_user_approved(event.sender_id) else "📊 Status: Inactive ❌"
        await event.reply(msg)

    else:
        if sleep_mode_active: await event.reply(OFFLINE_MSG)
        user = await event.get_sender()
        btns = [[Button.inline("💬 Reply", data=f"rep_{user.id}"), Button.inline("🚫 Block", data=f"blk_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`", buttons=btns)
        await client.forward_messages(config.ADMIN_ID, event.message)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
