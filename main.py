import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config, database, asyncio

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_fixed', config.API_ID, config.API_HASH)

# --- 1. WELCOME MESSAGE ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    # Save user to subscribers
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

    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. BUTTON LOGIC (FIXED) ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    # RESTORED: Exact professional text from your screenshot
    await event.reply("🛡️ **95%+ Accuracy Guaranteed.**\nEvery ticket is recorded and verified post-match. We maintain full transparency.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    # RESTORED: Professional terms
    await event.reply("⚖️ **Sales final. No reselling.**\nBy using this bot, you agree that all ticket purchases are non-refundable and for personal use only.")

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

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

# --- 4. ADMIN APPROVAL ---
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

# --- 5. STARTUP WITH FLOOD PROTECTION ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Bot Live & Buttons Fixed!**")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        logging.warning(f"FloodWait! Waiting {e.seconds}s.")
        await asyncio.sleep(e.seconds)
        await main()

if __name__ == '__main__':
    asyncio.run(main())
