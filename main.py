import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database

# REQUIRED: Enable logging to fix Railway "Starting Container" hang
logging.basicConfig(level=logging.INFO)

# Change session name slightly to clear any old locks
client = TelegramClient('mr_white_session_final', config.API_ID, config.API_HASH)

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
        # REINFORCED NEW USER ALERT
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`\nTotal Users: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    welcome = f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\n⭐ **CONFIRMED TICKET** 🎫\nTo see today's ticket, check the price via the link below, then click 'Claim'."
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome, buttons=buttons)

# --- STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # FIXED: Properly checks for 24h active access
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- BROADCAST ---
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

# --- BUTTON CALLBACKS (EXACT MESSAGES) ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    await event.reply("🛡️ **Mr. White Win Guarantee**\n\nWe provide high-accuracy Correct Score selections with a **95%+ success rate**. Results are verified post-match.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    await event.reply("⚖️ **Terms of Service**\n\n1. **Final Sale:** All purchases are final.\n2. **Verification:** Claims are verified manually.\n3. **Confidentiality:** Reselling is strictly prohibited.")

@client.on(events.CallbackQuery(data="how_to_pay"))
async def htp(event):
    await event.answer()
    guide = "📖 **How to Pay Guide**\n\n1️⃣ Click the **Check Price & Buy Ticket** link.\n2️⃣ Select your currency.\n3️⃣ Complete payment on Selar.\n4️⃣ Return here and click **'I Have Paid'**."
    await event.reply(guide)

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
        success_msg = "✅ **Payment Verified**\n\nYour ticket has been successfully issued and is valid for 24 hours.\nFor any issues or inquiries, /support"
        await client.send_file(uid, config.TICKET_URL, caption=success_msg)
        await event.edit(f"✅ User {uid} Approved.")
    else:
        reject_msg = "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Please check your payment details and try again or contact @Best_Admin24 for assistance."
        await client.send_message(uid, reject_msg)
        await event.edit(f"❌ User {uid} Rejected.")

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Mr. White Bot is Online!**")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
