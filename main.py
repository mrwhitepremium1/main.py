import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config, database, asyncio

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_broadcast_v16', config.API_ID, config.API_HASH)

# --- 1. THE ADVANCED BROADCAST COMMAND (TEXT + IMAGE) ---
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID:
        return
    
    # Extract text from the message (after the command)
    msg_text = event.raw_text.replace('/broadcast', '').strip()
    photo = event.photo if event.photo else None
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    users = cur.fetchall()
    cur.close(); conn.close()

    if not users:
        await event.reply("❌ No subscribers found in database.")
        return

    await event.reply(f"📣 Starting broadcast to {len(users)} users...")
    
    success_count = 0
    for user in users:
        try:
            if photo:
                await client.send_file(user[0], photo, caption=msg_text)
            else:
                await client.send_message(user[0], msg_text)
            
            success_count += 1
            await asyncio.sleep(0.3) # Protection against Telegram Flood
        except Exception as e:
            logging.error(f"Failed to send to {user[0]}: {e}")

    await event.reply(f"✅ Broadcast complete! Successfully sent to {success_count} users.")

# --- 2. START & NOTIFICATION ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user.id, user.username))
    conn.commit(); cur.close(); conn.close()

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

    # Using timestamp trick to prevent cache issues
    import time
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- 4. BUTTON CALLBACKS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    await event.reply("🛡️ **95%+ Accuracy Guaranteed.**\nEvery ticket is recorded and verified post-match.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    await event.reply("⚖️ **Terms:** Sales final. No reselling. Manual verification required.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 5. ADMIN APPROVAL LOGIC ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if act == "app":
        database.approve_user_24h(uid, "User")
        success = "✅ **Payment Verified**\nYour ticket is valid for 24 hours."
        await client.send_file(uid, config.TICKET_URL, caption=success)
        await event.edit(f"✅ Approved User {uid}")
    else:
        reject = "❌ **Payment Claim Rejected**\nContact @Best_Admin24 for assistance."
        await client.send_message(uid, reject)
        await event.edit(f"❌ Rejected User {uid}")

# --- 6. STARTUP ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Bot Online! Broadcast supports text & photos.**")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        logging.warning(f"FloodWait! Waiting {e.seconds}s.")
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
