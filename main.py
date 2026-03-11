from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & NEW USER ALERT ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection()
    cur = conn.cursor()
    
    # Check if user is in database
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        # New user found!
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        
        # Count total users
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        
        # ALERT ADMIN IMMEDIATELY
        try:
            alert = f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`\nTotal Users: {total}"
            await client.send_message(config.ADMIN_ID, alert)
        except Exception as e:
            print(f"Alert failed: {e}")

    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome = f"""Hello 👋 {first_name}!
**Welcome to Mr. White | Official Bot**

⭐ **CONFIRMED TICKET** 🎫
To see today's ticket, check the price via the link below, then click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome, buttons=buttons)

# --- 2. COMMANDS: STATUS & BROADCAST ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

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

# --- 3. CALLBACKS: GUARANTEE / TERMS / ADMIN ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer(); await event.reply("🛡️ 95%+ Accuracy Guaranteed.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer(); await event.reply("⚖️ No reselling. All sales final.")

@client.on(events.CallbackQuery(data="how_to_pay"))
async def htp(event):
    await event.answer(); await event.reply("📖 Link > Pay > Click 'Claim'.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
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
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Verified!** Access active for 24h.")
        await event.edit(f"✅ Approved {uid}")
    else:
        await client.send_message(uid, "❌ **Rejected.** Contact support.")
        await event.edit(f"❌ Rejected {uid}")

# --- 4. STARTUP ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        # STARTUP ALERT: Let's you know the bot is finally running
        await client.send_message(config.ADMIN_ID, "🚀 **Bot is Online & Database Connected!**")
        print("Bot is Online")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
