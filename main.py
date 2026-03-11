from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`\nTotal: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
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

**Price:** $20 USD / 150 GHS / 20,000 NGN

To see today's full ticket, please pay via the link and click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. INFORMATION HANDLERS ---

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer()
    guide = """📖 **How to Pay Guide**

1️⃣ Click the **Pay via Selar** link.
2️⃣ Select your currency (USD, GHS, NGN, etc.) at the top of the page.
3️⃣ Enter your Name and Email.
4️⃣ Choose your payment method (Card or Mobile Money).
5️⃣ Once payment is successful, return here and click 'I Have Paid (Claim)'."""
    await event.reply(guide)

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer()
    text = """🛡️ **Mr. White Win Guarantee**

We pride ourselves on delivering high-accuracy Correct Score selections. Our team performs deep analysis on team form, injuries, and historical data to ensure a **95%+ success rate**.

• **Verified Results:** Every ticket is recorded and verified post-match.
• **Transparency:** We do not delete past results; we let our history speak for itself.
• **Risk Note:** While our accuracy is industry-leading, betting involves risk. We advise responsible play."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer()
    text = """⚖️ **Terms of Service**

By utilizing Mr. White Official Bot services, you agree to the following:

1. **Final Sale:** Due to the nature of digital information, all ticket purchases are final. No refunds are issued after a ticket has been accessed.
2. **Verification:** Payment "Claims" are subject to manual admin verification. Fraudulent claims will result in a permanent ban.
3. **Confidentiality:** Sharing or reselling purchased tickets is strictly prohibited."""
    await event.reply(text)

# --- 3. ADMIN DECISION HANDLERS (FIXED) ---

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), 
             Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    data = event.data.decode().split('_')
    action, uid = data[0], int(data[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        success_msg = """✅ **Payment Verified**

Your ticket has been successfully issued and is valid for 24 hours.
For any issues or inquiries, /support"""
        await client.send_file(uid, config.TICKET_URL, caption=success_msg)
        await event.edit(f"✅ User {uid} Approved.")
    else:
        reject_msg = """❌ **Payment Claim Rejected**

Your payment could not be verified. Please check your payment details and try again or contact @Best_Admin24 for assistance."""
        await client.send_message(uid, reject_msg)
        await event.edit(f"❌ User {uid} Rejected.")

# --- 4. BROADCAST COMMAND (FIXED) ---

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg_text = event.text.replace('/broadcast', '').strip()
    if not msg_text: return await event.reply("❌ Usage: `/broadcast [message]`")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    sent_count = 0
    for u in users:
        try:
            await client.send_message(u[0], msg_text)
            sent_count += 1
            await asyncio.sleep(0.05) # Rate limiting
        except: continue
    await event.reply(f"✅ Broadcast sent to {sent_count} users.")

# --- 5. STARTUP ---

async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot is online!")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: Waiting {e.seconds}s...")
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
