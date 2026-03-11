import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database

# Fixes the "Starting Container" hang by showing real logs
logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_production_v8', config.API_ID, config.API_HASH)

# --- 1. WELCOME & NEW USER ALERT ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        # Admin Alert
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`\nTotal Users: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = f"""Hello 👋 {first_name}!

**Welcome to Mr. White | Official Bot**
━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM INFO ARRIVED**
⭐ **CONFIRMED TICKET** 🎫

☑ **Fixed Tips:** Correct Score
✔ **Verification:** 100% Guaranteed

To access today's confirmed selections, please check the price via the link below and click **'I Have Paid'**."""

    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. COMMANDS: STATUS, SUPPORT, BROADCAST ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE** ✅")
    else:
        await event.reply("📊 **Status:** Your access is **INACTIVE** ❌\nPlease purchase a ticket to activate.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance with payments or tickets.")

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_cmd(event):
    if event.sender_id != config.ADMIN_ID: return
    msg = event.text.replace('/broadcast', '').strip()
    if not msg: return await event.reply("Usage: /broadcast [message]")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    for u in users:
        try:
            await client.send_message(u[0], msg)
            await asyncio.sleep(0.05)
        except: continue
    await event.reply("✅ Broadcast Finished.")

# --- 3. CALLBACKS: GUARANTEE & TERMS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    text = """🛡️ **Mr. White Win Guarantee**

We pride ourselves on delivering high-accuracy Correct Score selections. Our team performs deep analysis to ensure a **95%+ success rate**.

• **Verified Results:** Every ticket is recorded and verified post-match.
• **Transparency:** We do not delete past results."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    text = """⚖️ **Terms of Service**

By utilizing Mr. White Official Bot services, you agree to the following:

1. **Final Sale:** All purchases are final.
2. **Verification:** Claims are subject to manual admin verification.
3. **Confidentiality:** Reselling tickets is strictly prohibited."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 4. ADMIN APPROVE/REJECT LOGIC ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if act == "app":
        database.approve_user_24h(uid, "User")
        success_msg = """✅ **Payment Verified**

Your ticket has been successfully issued and is valid for 24 hours."""
        await client.send_file(uid, config.TICKET_URL, caption=success_msg)
        await event.edit(f"✅ Approved User {uid}")
    else:
        reject_msg = """❌ **Payment Claim Rejected**

Your payment could not be verified. Please check your payment details and try again or contact @Best_Admin24 for assistance."""
        await client.send_message(uid, reject_msg)
        await event.edit(f"❌ Rejected User {uid}")

# --- 5. STARTUP & LAUNCHED MESSAGE ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        
        launch_text = """🚀 **Mr. White Bot Successfully Launched!**
━━━━━━━━━━━━━━━━━━━━
✅ **Connection:** Established
✅ **Database:** Connected
✅ **Admin Alerts:** Active
✅ **Broadcast System:** Ready"""
        
        await client.send_message(config.ADMIN_ID, launch_text)
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
