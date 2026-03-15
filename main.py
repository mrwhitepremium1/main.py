import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config, database, asyncio, time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v29_fixed', config.API_ID, config.API_HASH)

# --- 1. MULTI-LINE BROADCAST & AUTO-CLEAN ---
@client.on(events.NewMessage(pattern=r'/(broadcast|boardcast)([\s\S]*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    
    if not msg_text and not photo:
        await event.reply("❌ **Error:** Please type a message or attach a photo.")
        return
        
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    progress_msg = await event.reply(f"📣 **Broadcasting to {len(users)} users...**")
    success_count = 0; blocked_count = 0
    
    for user in users:
        uid = user[0]
        try:
            if photo: await client.send_file(uid, photo, caption=msg_text)
            else: await client.send_message(uid, msg_text)
            success_count += 1
            await asyncio.sleep(0.3) # Protection against Telegram Flood
        except (UserIsBlockedError, PeerIdInvalidError):
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
            conn.commit(); cur.close(); conn.close()
            blocked_count += 1
        except Exception: continue
        
    await progress_msg.edit(f"✅ **Broadcast complete!**\nSent: **{success_count}**\nRemoved: **{blocked_count}**")

# --- 2. START COMMAND (Tracking & Alerts) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    now = datetime.now()
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, last_seen) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) DO UPDATE SET last_seen = EXCLUDED.last_seen, username = EXCLUDED.username
    """, (user.id, user.username, now))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()

    # Admin Alert
    alert = (f"👤 **Visitor Alert!**\nName: {first_name}\nUsername: @{user.username if user.username else 'N/A'}\n"
             f"ID: `{user.id}`\nTotal Users: {total}")
    await client.send_message(config.ADMIN_ID, alert)

    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access selections, please check "
                    f"the price and click **'I Have Paid'**.")
    
    # Anti-cache trick for the ticket image
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. STATS COMMAND ---
@client.on(events.NewMessage(pattern='/stats'))
async def stats_cmd(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
    yesterday = datetime.now() - timedelta(days=1)
    cur.execute("SELECT COUNT(*) FROM subscribers WHERE last_seen > %s", (yesterday,))
    active_24h = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Bot Statistics**\n\n👥 Total Subscribers: **{total}**\n🔥 Active (Last 24h): **{active_24h}**")

# --- 4. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: Active 🤝**\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 **Status: Inactive ❌**\n\nYour subscription is currently inactive.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **Connected to support.**\nExplain your issue clearly, Mr. White is listening. 🎯")

# --- 5. LIVE CHAT & ADMIN REPLY ---
@client.on(events.NewMessage(incoming=True))
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"📩 **NEW MESSAGE**\n👤 **From:** {user.first_name}\n🆔 **ID:** `{event.sender_id}`\n\n💬 **Message:**\n{event.raw_text}")
        if 0 <= datetime.utcnow().hour < 5:
            await event.reply("🌙 **Mr. White is offline.**\nI will review this after 5 AM. Thank you! 🎯")

@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    user_id = int(event.pattern_match.group(1)); reply_msg = event.pattern_match.group(2).strip()
    try:
        await client.send_message(user_id, f"👨‍💼 **Mr. White Support:**\n\n{reply_msg}")
        await event.reply(f"✅ Reply sent to `{user_id}`")
    except Exception: await event.reply("❌ User may have blocked the bot.")

# --- 6. CALLBACKS & ADMIN ACTIONS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.reply("🛡️ **Win Guarantee**\nDeep analysis on every match. Target accuracy 95%+.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.reply("⚖️ **Terms**\n1. All sales final. 2. Manual verification required.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Payment Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if act == "app":
        database.approve_user(uid, "User") # Fixed to match your database function name
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\nYour ticket has been issued!")
        await event.edit(f"✅ Approved User {uid}")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nContact @best_admin24 for help.")
        await event.edit(f"❌ Rejected User {uid}")

# --- 7. DATABASE REPAIR & RUNNER ---
async def main():
    try:
        database.init_db()
        # Ensure the subscribers table has the last_seen column
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS username TEXT")
        conn.commit(); cur.close(); conn.close()
        
        await client.start(bot_token=config.BOT_TOKEN)
        print("🚀 BOT IS FULLY REPAIRED & LIVE!")
        await client.run_until_disconnected()
    except FloodWaitError as e: 
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
