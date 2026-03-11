from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & COMMAND HANDLERS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {first_name}\nID: `{user.id}`")
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

@client.on(events.NewMessage(pattern='/price'))
async def price_cmd(event):
    await event.reply("**Price List:**\n$20 USD / 150 GHS / 20,000 NGN\n\nPay here: " + config.SELAR_PAYMENT_LINK)

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    await event.reply("📊 **Status:** Your access is currently inactive. Please purchase a ticket to activate.")

# --- 2. INFORMATION CALLBACKS ---

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer()
    guide = """📖 **How to Pay Guide**
1️⃣ Click the **Pay via Selar** link.
2️⃣ Select your currency (USD, GHS, NGN, etc.) at the top.
3️⃣ Enter Name and Email.
4️⃣ Pay via Card or Mobile Money.
5️⃣ Return here and click 'I Have Paid (Claim)'."""
    await event.reply(guide)

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer()
    text = """🛡️ **Mr. White Win Guarantee**
We provide high-accuracy Correct Score selections with a **95%+ success rate**. Results are verified post-match. Transparency is our priority."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer()
    text = """⚖️ **Terms of Service**
1. All digital sales are final.
2. Claims are subject to manual verification.
3. Reselling or sharing tickets is strictly prohibited."""
    await event.reply(text)

# --- 3. ADMIN DECISION LOGIC (CRITICAL FIX) ---

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Request sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), 
             Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# Pattern matches 'app_12345' or 'rej_12345'
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    
    data = event.data.decode().split('_')
    action = data[0]
    target_id = int(data[1])
    
    if action == "app":
        database.approve_user_24h(target_id, "User")
        success_msg = """✅ **Payment Verified**

Your ticket has been successfully issued and is valid for 24 hours.
For any issues or inquiries, /support"""
        await client.send_file(target_id, config.TICKET_URL, caption=success_msg)
        await event.edit(f"✅ User {target_id} Approved.")
    else:
        reject_msg = """❌ **Payment Claim Rejected**

Your payment could not be verified. Please check your payment details and try again or contact @Best_Admin24 for assistance."""
        await client.send_message(target_id, reject_msg)
        await event.edit(f"❌ User {target_id} Rejected.")

# --- 4. BROADCAST COMMAND (FIXED) ---

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_cmd(event):
    if event.sender_id != config.ADMIN_ID: return
    message = event.text.replace('/broadcast', '').strip()
    if not message:
        return await event.reply("❌ Usage: `/broadcast [your message]`")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    count = 0
    for u in users:
        try:
            await client.send_message(u[0], message)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await event.reply(f"✅ Broadcast sent to {count} users.")

# --- 5. RUN BOT ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Mr. White Bot Online")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
