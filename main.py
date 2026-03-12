import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config, database, asyncio, time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v28_final', config.API_ID, config.API_HASH)

# --- 1. MULTI-LINE BROADCAST & AUTO-CLEAN ---
@client.on(events.NewMessage(pattern=r'/(broadcast|boardcast)([\s\S]*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    if not msg_text and not photo:
        await event.reply("❌ **Error:** Please type a message after the command.")
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
            await asyncio.sleep(0.3)
        except (UserIsBlockedError, PeerIdInvalidError):
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
            conn.commit(); cur.close(); conn.close()
            blocked_count += 1
        except Exception: continue
    await progress_msg.edit(f"✅ **Broadcast complete!**\nSent: **{success_count}**\nRemoved: **{blocked_count}**")

# --- 2. START COMMAND (Alerts + Last Seen) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, username, last_seen) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id) DO UPDATE SET last_seen = EXCLUDED.last_seen, username = EXCLUDED.username
    """, (user.id, user.username, datetime.now()))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()

    # Admin Alert
    alert = (f"👤 **Visitor Alert!**\nName: {first_name}\nUsername: @{user.username if user.username else 'N/A'}\n"
             f"ID: `{user.id}`\nTime: `{current_time_str}`\nTotal Users: {total}")
    await client.send_message(config.ADMIN_ID, alert)

    buttons = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
               [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check "
                    f"the price via the link below and click **'I Have Paid'**.")
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
        await event.reply("📊 **Status: Inactive ❌**\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **You’re now connected to support.**\nKindly explain your issue clearly Mr. White is listening. 🎯")

# --- 5. LIVE CHAT & OFFLINE AUTO-REPLY ---
@client.on(events.NewMessage(incoming=True))
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"📩 **NEW SUPPORT MESSAGE**\n👤 **From:** {user.first_name}\n🆔 **ID:** `{event.sender_id}`\n\n💬 **Message:**\n{event.raw_text}")
        if 0 <= datetime.utcnow().hour < 5:
            await event.reply("🌙 **Mr. White is currently offline.**\n\nI have received your message and will review it as soon as I am back online in the morning (after 5 AM). Thank you for your patience! 🎯")

# --- 6. ADMIN REPLY ---
@client.on(events.NewMessage(pattern=r'/reply (\d+) ([\s\S]*)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    user_id = int(event.pattern_match.group(1)); reply_msg = event.pattern_match.group(2).strip()
    try:
        await client.send_message(user_id, f"👨‍💼 **Mr. White Support:**\n\n{reply_msg}")
        await event.reply(f"✅ Reply sent to `{user_id}`")
    except Exception: await event.reply("❌ Error: User may have blocked the bot.")

# --- 7. CALLBACKS (WIN GUARANTEE & TERMS) ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer(); await event.reply("🛡️ **Mr. White Win Guarantee**\n\nWe take pride in delivering high-accuracy Correct Score selections.\nOur team conducts deep analysis and research on every match to provide carefully selected tips with a target accuracy of 95%+.\n\nOur goal is simple: consistency, transparency, and long-term trust with every subscriber.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer(); await event.reply("⚖️ **Terms of Service**\n\n1. **Final Sale:** All purchases are final and non-refundable.\n2. **Verification:** Payment claims and access requests are subject to manual admin verification before approval.\n3. **Confidentiality:** Reselling, sharing, or redistributing tickets is strictly prohibited and may result in permanent removal.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 8. ADMIN ACTIONS (APPROVED & REJECTED) ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer(); act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if act == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified**\n\nYour payment has been successfully confirmed.\nYour ticket has been issued and will remain valid for 24 hours.")
        await event.edit(f"✅ Approved User {uid}")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\n\nYour payment could not be verified at this time.\nPlease contact Mr White for assistance.\n\nCommand: /support")
        await event.edit(f"❌ Rejected User {uid}")

# --- 9. RUNNER ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN); database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Bot Online! Alerts, Stats, and Last Seen tracking active.**")
        await client.run_until_disconnected()
    except FloodWaitError as e: await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__': asyncio.run(main())
