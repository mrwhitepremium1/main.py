import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config, database, asyncio, time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_v23', config.API_ID, config.API_HASH)

# --- 1. TYPO-PROOF BROADCAST ---
@client.on(events.NewMessage(pattern=r'/(broadcast|boardcast)(.*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID:
        return
    
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    
    if not msg_text and not photo:
        await event.reply("❌ **Error:** Please type a message after the command.\nExample: `/broadcast Hello everyone!`")
        return

    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    users = cur.fetchall()
    cur.close(); conn.close()

    if not users:
        await event.reply("❌ No subscribers found in database.")
        return

    progress_msg = await event.reply(f"📣 **Sending to {len(users)} users...**")
    
    success_count = 0
    for user in users:
        try:
            if photo:
                await client.send_file(user[0], photo, caption=msg_text)
            else:
                await client.send_message(user[0], msg_text)
            success_count += 1
            await asyncio.sleep(0.3)
        except Exception:
            continue

    await progress_msg.edit(f"✅ **Broadcast complete!**\nSuccessfully sent to **{success_count}** users.")

# --- 2. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user.id, user.username))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
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

    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. STATUS & SUPPORT SYSTEM ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    # This is the exact message you requested!
    await event.reply("💬 **You’re now connected to support.**\nKindly explain your issue clearly Mr. White is listening. 🎯")

# --- 4. LIVE CHAT FORWARDING & AUTO-REPLY (12AM - 5AM) ---
@client.on(events.NewMessage(incoming=True))
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        user = await event.get_sender()
        name = user.first_name if user.first_name else "Unknown"
        
        # Forward message to Admin
        await client.send_message(
            config.ADMIN_ID, 
            f"📩 **NEW SUPPORT MESSAGE**\n👤 **From:** {name}\n🆔 **ID:** `{event.sender_id}`\n\n💬 **Message:**\n{event.raw_text}"
        )
        
        # Check current hour in GMT (0 to 23)
        current_hour = datetime.utcnow().hour
        
        # Offline window: 12 AM (0) to 5 AM (5)
        if 0 <= current_hour < 5:
            await event.reply("🌙 **Mr. White is currently offline.**\n\nI have received your message and will review it as soon as I am back online in the morning (after 5 AM). Thank you for your patience! 🎯")

# --- 5. ADMIN REPLY COMMAND ---
@client.on(events.NewMessage(pattern=r'/reply (\d+) (.+)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID:
        return
    
    user_id = int(event.pattern_match.group(1))
    reply_msg = event.pattern_match.group(2)
    
    try:
        await client.send_message(user_id, f"👨‍💼 **Mr. White Support:**\n\n{reply_msg}")
        await event.reply(f"✅ Reply successfully sent to user `{user_id}`")
    except Exception as e:
        await event.reply(f"❌ Failed to send message: {e}")

# --- 6. BUTTON CALLBACKS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    await event.reply("🛡️ **95%+ Accuracy Guaranteed.**\nEvery ticket is analyzed and verified post-match.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    await event.reply("⚖️ **Terms:** Sales are final. Manual verification is required for all claims.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 7. ADMIN ACTIONS ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if act == "app":
        database.approve_user_24h(uid, "User")
        success = "✅ **Payment Verified**\nYour ticket has been issued and is valid for 24 hours."
        await client.send_file(uid, config.TICKET_URL, caption=success)
        await event.edit(f"✅ Approved User {uid}")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nPlease ensure you have paid via Selar.")
        await event.edit(f"❌ Rejected User {uid}")

# --- 8. MAIN RUNNER ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Bot Online! Support offline from 12AM-5AM.**")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        logging.warning(f"FloodWait! Waiting {e.seconds}s.")
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
