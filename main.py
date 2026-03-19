import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config
import database

# --- SETTINGS ---
SESSION = 'mr_white_vision_v65'
logging.basicConfig(level=logging.INFO)
client = TelegramClient(SESSION, config.API_ID, config.API_HASH)

# Global State
pending_replies = {}
sleep_mode_active = False
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed shortly. 🎯"

# --- 1. ADMIN GATEKEEPER (COMMANDS & QUICK REPLIES) ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_handler(event):
    global sleep_mode_active, pending_replies
    text = event.raw_text.strip()
    cmd = text.lower()

    # Handle Quick Reply Logic
    if config.ADMIN_ID in pending_replies and not text.startswith('/'):
        target_uid = pending_replies.pop(config.ADMIN_ID)
        try:
            header = "👨‍💼 **Mr. White Support:**\n\n"
            await client.send_message(target_uid, f"{header}{text}")
            await event.reply(f"✅ **Sent to `{target_uid}`**")
        except:
            await event.reply("❌ **Failed.** User might have blocked the bot.")
        return

    # Admin Commands
    if cmd == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM subscribers")
        users = cur.fetchall(); cur.close(); conn.close()
        msg = f"📊 **Subscribers ({len(users)})**\n" + "━" * 15 + "\n"
        for u_id, u_name in users:
            msg += f"🆔 `{u_id}` | @{u_name if u_name else 'None'}\n"
        await event.reply(msg)

    elif cmd == '/broadcast':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall(); cur.close(); conn.close()
        
        bc_msg = ("💎 **NEW: AUTOMATIC CRYPTO PAYMENTS**\n━━━━━━━━━━━━━━━━━━━━\n"
                  "We have upgraded! Pay with **Crypto** for instant access.\n\n"
                  "✅ **Instant Verification**\n🎫 **Automatic Ticket Pop-up**\n"
                  "🔗 **Pay here:** https://pay.oxapay.com/10368962")
        
        await event.reply(f"🚀 **Broadcasting to {len(users)} users...**")
        for u in users:
            try:
                await client.send_message(u[0], bc_msg, buttons=[[Button.url("💰 Pay Crypto", "https://pay.oxapay.com/10368962")]])
                await asyncio.sleep(5.0) # Safety Delay
            except: continue
        await event.reply("✅ **Broadcast Complete.**")

# --- 2. USER HANDLER (START & FORWARDING) ---
@client.on(events.NewMessage(incoming=True))
async def user_handler(event):
    if event.sender_id == config.ADMIN_ID: return # STOP FEEDBACK LOOP
    
    uid = event.sender_id
    text = event.raw_text.strip().lower()

    if text == '/start':
        sender = await event.get_sender()
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, sender.username, datetime.now(), datetime.now()))
        conn.commit(); cur.close(); conn.close()
        
        welcome = (f"Hello 👋 {sender.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                   "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫")
        btns = [[Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
                [Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
                [Button.inline("✅ I Have Paid", data="claim_pay")]]
        
        await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)
        
        # Admin Notification with Control Buttons
        admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {sender.first_name}\nID: `{uid}`", buttons=admin_btns)
    
    else:
        # Standard Forwarding to Admin
        admin_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
        await client.send_message(config.ADMIN_ID, f"📩 **MESSAGE FROM `{uid}`**", buttons=admin_btns)
        await client.forward_messages(config.ADMIN_ID, event.message)

# --- 3. CALLBACK HANDLER (BLOCK & REPLY) ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()
    
    if data.startswith('qr_'):
        uid = int(data.split('_')[1])
        pending_replies[config.ADMIN_ID] = uid
        await event.answer("✍️ Type your reply now...", alert=True)

    elif data.startswith('preblk_'):
        uid = int(data.split('_')[1])
        btns = [[Button.inline("✅ YES, BLOCK", data=f"confblk_{uid}")], [Button.inline("❌ CANCEL", data="cancel")]]
        await event.edit(f"⚠️ **Block `{uid}`?**", buttons=btns)

    elif data.startswith('confblk_'):
        uid = int(data.split('_')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 **User `{uid}` Blocked.**")

    elif data == "cancel":
        await event.edit("✅ **Action Cancelled.**")

    elif data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM!**\nID: `{user.id}`", 
                                  buttons=[[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("💬 Reply", data=f"qr_{user.id}")]])

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        print("✅ Mr. White Vision Master Online.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"🛑 Wait {e.seconds}s")

if __name__ == '__main__': asyncio.run(main())
