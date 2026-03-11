from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & STATUS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
    cur.close(); conn.close()

    # Updated button text to refer users to Selar for pricing
    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
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

To see today's full ticket, please check the price and buy your ticket via the link below, then click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # Checks database for 24h active purchase status
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE**. You have full access to current tickets.")
    else:
        await event.reply("📊 **Status:** Your access is currently **INACTIVE**. Please purchase a ticket to activate.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- 2. INFORMATION BUTTONS ---

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer() 
    text = """🛡️ **Mr. White Win Guarantee**

We pride ourselves on delivering high-accuracy Correct Score selections.

• **Verified Results:** Every ticket is recorded and verified post-match.
• **Transparency:** We do not delete past results.
• **Risk Note:** Betting involves risk. We advise responsible play."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer()
    text = """⚖️ **Terms of Service**

By utilizing Mr. White Official Bot services, you agree to the following:

1. **Final Sale:** All ticket purchases are final.
2. **Verification:** Claims are subject to manual admin verification.
3. **Confidentiality:** Sharing or reselling tickets is strictly prohibited."""
    await event.reply(text)

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer()
    guide = """📖 **How to Pay Guide**
1️⃣ Click the **Check Price & Buy Ticket** link.
2️⃣ Select your currency at the top of the page.
3️⃣ Enter your details and pay.
4️⃣ Return here and click 'I Have Paid (Claim)'."""
    await event.reply(guide)

# --- 3. ADMIN ACTIONS ---

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

Your payment could not be verified. Please check your details or contact @Best_Admin24."""
        await client.send_message(uid, reject_msg)
        await event.edit(f"❌ User {uid} Rejected.")

# --- 4. STARTUP ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot is online.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
