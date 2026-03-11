from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & REINFORCED USER ALERT ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    username = f"@{user.username}" if user.username else "No Username"
    
    conn = database.get_connection()
    cur = conn.cursor()
    
    # Check if user is new
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    is_new = cur.fetchone() is None
    
    if is_new:
        # Add new user to database
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        
        # Get total user count for the alert
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total_users = cur.fetchone()[0]
        
        # IMMEDIATE ADMIN ALERT (Fixed)
        alert_msg = f"""👤 **New Visitor Alert!**
━━━━━━━━━━━━━━━━━━━
📝 **Name:** {first_name}
🆔 **ID:** `{user.id}`
🔗 **Username:** {username}
📈 **Total Users:** {total_users}"""
        
        try:
            await client.send_message(config.ADMIN_ID, alert_msg)
        except Exception as e:
            print(f"Admin Alert Error: {e}")

    cur.close()
    conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = f"""Hello 👋 {first_name}!

**Welcome to Mr. White | Official Bot**

💎 **NEW INFO ARRIVED**
━━━━━━━━━━━━━━━━━━━
⭐ **CONFIRMED TICKET** 🎫
☑ **Fixed Tips:** Correct Score
✔ **Safe:** 💯 Guaranteed

To see today's full ticket, please check the price and buy your ticket via the link below, then click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. STATUS & BROADCAST ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE**.")
    else:
        await event.reply("📊 **Status:** Your access is currently **INACTIVE**.")

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_cmd(event):
    if event.sender_id != config.ADMIN_ID: return
    msg = event.text.replace('/broadcast', '').strip()
    if not msg: return await event.reply("❌ Usage: `/broadcast [message]`")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    count = 0
    for u in users:
        try:
            await client.send_message(u[0], msg)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await event.reply(f"✅ Broadcast sent to {count} users.")

# --- 3. RANDOM MESSAGE ASSISTANT ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def assistant(event):
    if event.text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    btn = [[Button.inline("🎫 View Ticket Info", data="trigger_start")]]
    await event.reply("🤖 **Mr. White Assistant:** Need help with today's ticket?", buttons=btn)

@client.on(events.CallbackQuery(data="trigger_start"))
async def cb_start(event):
    await event.answer(); await start(event)

# --- 4. CALLBACKS & ADMIN APPROVAL ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee(event):
    await event.answer()
    await event.reply("🛡️ **Mr. White Win Guarantee**\n95%+ success rate on Correct Scores.")

@client.on(events.CallbackQuery(data="terms"))
async def terms(event):
    await event.answer()
    await event.reply("⚖️ **Terms:** Sales final. No reselling.")

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay(event):
    await event.answer()
    await event.reply("📖 **How to Pay:** Link > Currency > Pay > 'I Have Paid'.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if act == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!** Ticket valid for 24h.")
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Rejected.** Contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot is online with reinforced alerts.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
