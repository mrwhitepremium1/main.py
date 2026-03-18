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

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v43', config.API_ID, config.API_HASH)

# --- 1. CALLBACK HANDLER (APPROVE / REJECT / PAYMENTS) ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    
    # Admin Logic: Approve
    if data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid, "User")
        await event.edit(f"✅ **Approved `{uid}`**")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!**\n\nYour ticket has been issued and your access is now active.")
    
    # Admin Logic: Reject
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ **Rejected `{uid}`**")
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Please contact support if you believe this is an error.")

    # User Logic: Payment Navigation
    elif data == "pay_options":
        btns = [
            [Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
            [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
            [Button.inline("⬅️ Back", data="back_start")]
        ]
        await event.edit("🎯 **Select your preferred payment method:**", buttons=btns)

    elif data == "pay_crypto":
        await event.edit("💎 **Cryptocurrency Payment**\n\nPrice: **40 USD**\n\nWe accept USDT, BTC, and more via OxaPay.", 
                         buttons=[[Button.url("🔗 Pay 40 USD", "https://pay.oxapay.com/10368962")],
                                  [Button.inline("⬅️ Back", data="pay_options")]])

    elif data == "back_start":
        # Returns user to the main menu without re-sending /start
        user = await event.get_sender()
        name = user.first_name if user.first_name else "Visitor"
        btns = [[Button.inline("💳 Check Price & Buy Ticket", data="pay_options")], [Button.inline("✅ I Have Paid", data="claim_pay")]]
        await event.edit(f"Hello 👋 {name}!\nSelect an option below:", buttons=btns)

    elif data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim Request!**\nName: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 2. ADMIN COMMANDS (FIND / BROADCAST / USERS / SLEEP) ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_commands(event):
    global sleep_mode_active
    text = event.raw_text.strip()

    # FIND USER
    if text.startswith('/find'):
        match = re.search(r'\d+', text)
        if match:
            uid = int(match.group())
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT username, last_seen FROM subscribers WHERE user_id = %s", (uid,))
            res = cur.fetchone()
            cur.close(); conn.close()
            if res:
                uname = f"@{res[0]}" if res[0] else "@No Username"
                await event.reply(f"🔍 **User Found:**\n🆔 ID: `{uid}`\n👤 User: {uname}\n🕒 Last Seen: {res[1]}")
            else: await event.reply("❌ User ID not found in database.")

    # BROADCAST (With Flood Protection)
    elif text.lower().startswith(('/broadcast', '/boardcast')):
        msg_body = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        progress = await event.reply("📣 **Starting Broadcast...**")
        count = 0
        for u in users:
            try:
                if event.media: await client.send_file(u[0], event.media, caption=msg_body)
                else: await client.send_message(u[0], msg_body)
                count += 1
                await asyncio.sleep(0.3)
            except FloodWaitError as e: await asyncio.sleep(e.seconds)
            except: continue
        await progress.edit(f"✅ **Broadcast Finished!**\nTotal Sent: {count}")

    # SLEEP MODE
    elif text.lower().startswith('/sleep'):
        sleep_mode_active = 'on' in text.lower()
        await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

    # USER COUNT
    elif text.lower() == '/users':
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
        cur.close(); conn.close()
        await event.reply(f"📊 **Total Database Subscribers: {total}**")

# --- 3. USER COMMANDS (START / STATUS / SUPPORT) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    # Log to Admin
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {user.first_name}\nID: `{user.id}`")
    # Save to DB
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (user.id, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()
    
    btns = [[Button.inline("💳 Check Price & Buy Ticket", data="pay_options")], [Button.inline("✅ I Have Paid", data="claim_pay")]]
    welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
               "✔ **Verification:** 100% Guaranteed")
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 Status: Active 🤝\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 Status: Inactive ❌\n\nYour subscription is currently inactive.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 4. MESSAGE FORWARDING (LAST PRIORITY) ---
@client.on(events.NewMessage())
async def forwarding_handler(event):
    # Only forward if it's a private message, NOT a command, and NOT from admin
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID:
        return
    
    if sleep_mode_active:
        await event.reply(OFFLINE_MSG)
        
    user = await event.get_sender()
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
    await client.forward_messages(config.ADMIN_ID, event.message)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
