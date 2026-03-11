from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

# Initialize Client
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
        # Admin Notification
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\n\nName: {first_name}\nUsername: @{user.username}\n📈 Total Users: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Pay $20 via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\n"
                    "💎 **NEW INFO ARRIVED**\n━━━━━━━━━━━━━━━━━━━\n"
                    "⭐ **CONFIRMED TICKET** 🎫\n☑ **Fixed Tips:** Correct Score\n✔ **Safe:** 💯 Guaranteed\n\n"
                    "**Price:** $20 USD / 150 GHS / 20,000 NGN\n\n"
                    "To see today's full ticket, please pay via the link and click 'Claim'.")
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. OFFICIAL PRICE LIST ---
@client.on(events.NewMessage(pattern='/price'))
async def price(event):
    price_text = (
        "🌍 **Mr. White Official Price List**\n"
        "*(Daily Access - Correct Score Ticket)*\n\n"
        "🇺🇸 **USD:** $20\n"
        "🇬🇭 **GHS:** 150 GHS\n"
        "🇳🇬 **NGN:** 20,000 NGN\n"
        "🇰🇪 **KES:** 2,000 KES\n"
        "🇿🇦 **ZAR:** 300 ZAR\n"
        "🇬🇧 **GBP:** £20\n"
        "🇿🇲 **ZMW:** 300 ZMW\n"
        "💶 **CFA:** 10,000 XAF/XOF\n\n"
        "✅ *Don't see your currency? Click below:* "
    )
    buttons = [
        [Button.inline("❓ My country is not listed", data="not_listed")],
        [Button.inline("📖 How to Pay", data="how_to_pay")],
        [Button.url("💳 Proceed to Payment", config.SELAR_PAYMENT_LINK)]
    ]
    await event.reply(price_text, buttons=buttons)

# --- 3. UPDATED INFORMATION CALLBACKS ---

@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer() # Clears loading spinner
    # Exact wording from screenshot
    guarantee_text = (
        "🛡️ **Mr. White Win Guarantee**\n\n"
        "We pride ourselves on delivering high-accuracy Correct Score selections. "
        "Our team performs deep analysis on team form, injuries, and historical data to ensure a **95%+ success rate**.\n\n"
        "• **Verified Results:** Every ticket is recorded and verified post-match.\n"
        "• **Transparency:** We do not delete past results; we let our history speak for itself.\n"
        "• **Risk Note:** While our accuracy is industry-leading, betting involves risk. We advise responsible play."
    )
    await event.reply(guarantee_text)

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer() # Clears loading spinner
    # Exact wording from screenshot
    terms_text = (
        "⚖️ **Terms of Service**\n\n"
        "By utilizing Mr. White Official Bot services, you agree to the following:\n\n"
        "1. **Final Sale:** Due to the nature of digital information, all ticket purchases are final. "
        "No refunds are issued after a ticket has been accessed.\n"
        "2. **Verification:** Payment \"Claims\" are subject to manual admin verification. "
        "Fraudulent claims will result in a permanent ban.\n"
        "3. **Confidentiality:** Sharing or reselling purchased tickets is strictly prohibited "
        "and will result in the immediate termination of access."
    )
    await event.reply(terms_text)

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay(event):
    await event.answer()
    guide = (
        "📖 **How to Pay Guide**\n\n"
        "1️⃣ Click the **Pay** link.\n"
        "2️⃣ Select your currency & payment method.\n"
        "3️⃣ Complete payment on the secure Selar page.\n"
        "4️⃣ Return here and click '**I Have Paid (Claim)**'.\n"
        "5️⃣ Wait for admin verification to receive your ticket."
    )
    await event.reply(guide)

@client.on(events.CallbackQuery(data="not_listed"))
async def not_listed(event):
    await event.answer()
    await event.reply("🌍 **Global Support**\n\nSelar supports 190+ countries. It will auto-convert $20 USD to your local currency at checkout.")

# --- 4. PAYMENT CLAIM & ADMIN ---
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
    action, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if action == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!** Here is your ticket.")
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Rejected.** Contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

# --- 5. AUTO-REPLY LOGIC ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_reply(event):
    if event.text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    buttons = [[Button.inline("🎫 View Ticket", data="show_start_logic")],
               [Button.inline("💰 Price List", data="show_price_logic")]]
    await event.reply("🤖 **Mr. White Assistant:** How can I help you today?", buttons=buttons)

@client.on(events.CallbackQuery(data="show_start_logic"))
async def cb_start(event): await event.answer(); await start(event)

@client.on(events.CallbackQuery(data="show_price_logic"))
async def cb_price(event): await event.answer(); await price(event)

# --- 6. RESILIENT STARTUP ---
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
