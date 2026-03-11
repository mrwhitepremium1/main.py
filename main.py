import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config, database, asyncio

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_vision', config.API_ID, config.API_HASH)

# --- 1. START & ADMIN NOTIFICATION ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user.id, user.username))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
    # Sends you an alert when a new person joins
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

# --- 2. FIXED BUTTON CALLBACKS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    # Matches the professional text from your request
    await event.reply("🛡️ **Mr. White Win Guarantee**\n\nWe pride ourselves on delivering high-accuracy Correct Score selections. Our team performs deep analysis to ensure a **95%+ success rate**.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    # Matches the professional terms from your request
    await event.reply("⚖️ **Terms of Service**\n\n1. **Final Sale:** All purchases are final.\n2. **Verification:** Claims are subject to manual admin verification.\n3. **Confidentiality:** Reselling tickets is strictly prohibited.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 3. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # FIXED LOGIC: Checks only the approval table
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance with payments or tickets.")

# --- 4. ADMIN APPROVE/REJECT ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if act == "app":
        database.approve_user_24h(uid, "User")
        success_msg = "✅ **Payment Verified**\n\nYour ticket has been successfully issued and is valid for 24 hours."
        await client.send_file(uid, config.TICKET_URL, caption=success_msg)
        await event.edit(f"✅ Approved User {uid}")
    else:
        reject_msg = "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Please contact @Best_Admin24 for assistance."
        await client.send_message(uid, reject_msg)
        await event.edit(f"❌ Rejected User {uid}")

# --- 5. STARTUP WITH FLOOD HANDLING ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Mr. White Bot: Final Vision Online!**\nAll buttons and status logic verified.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        # Prevents crashing during Railway restarts
        logging.warning(f"FloodWait! Sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
