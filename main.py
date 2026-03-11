from telethon import TelegramClient, events, Button
import config
import database
import os

# Initialize Client
client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)
database.init_db()

# --- 1. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        # Visitor Alert
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\n\nName: {first_name}\nUsername: @{user.username}\n📈 Total Users: {total}")
    cur.close(); conn.close()

    buttons = [[Button.url("💳 Pay $15 via Selar", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\n"
                    "💎 **NEW INFO ARRIVED**\n━━━━━━━━━━━━━━━━━━━\n"
                    "⭐ **CONFIRMED TICKET** 🎫\n☑ **Fixed Tips:** Correct Score\n✔ **Safe:** 💯 Guaranteed\n\n"
                    "**Price:** $15 USD (Daily Access)\n\n"
                    "To see today's full uncovered ticket, please pay via the link and click 'Claim'.")
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. INTERNATIONAL PRICE LIST ---
@client.on(events.NewMessage(pattern='/price'))
async def price(event):
    price_text = (
        "🌍 **Mr. White Official - Daily Ticket**\n\n"
        "⭐ **Price:** $15 USD\n"
        "⏳ **Validity:** 24 Hours Access\n\n"
        "💱 **Estimated Local Rates:**\n"
        "• 🇬🇭 GHS: ~245 GHS\n"
        "• 🇳🇬 NGN: ~24,000 NGN\n"
        "• 🇰🇪 KES: ~2,000 KES\n\n"
        "💡 *Accepted in 190+ countries. Selar will automatically convert your currency to $15 USD at checkout.*"
    )
    await event.reply(price_text)

# --- 3. MENU COMMANDS ---
@client.on(events.NewMessage(pattern='/support'))
async def support(event):
    await event.reply("👋 **Need help?**\n\nContact our official admin: @Best_Admin24")

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("✅ **Active:** You have full access for 24 hours.")
    else:
        await event.reply("❌ **Inactive:** No active ticket found. Use /start to buy.")

# --- 4. BROADCAST (Admin Only) ---
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    msg = event.text.replace('/broadcast', '').strip()
    if not msg: return await event.reply("❌ Usage: /broadcast [message]")
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    count = 0
    for u in users:
        try: await client.send_message(u[0], msg); count += 1
        except: continue
    await event.reply(f"✅ Broadcast sent to {count} users.")

# --- 5. CALLBACKS (Button Logic) ---
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
        cap = "✅ **Payment Verified**\n\nYour ticket is issued (24h valid).\nContact: @Best_Admin24"
        await client.send_file(uid, config.TICKET_URL, caption=cap)
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nPlease check details or contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

# --- 6. AUTO-REPLY & CALLBACKS ---
@client.on(events.CallbackQuery(data="show_start_logic"))
async def show_start(event):
    await event.answer()
    await start(event)

@client.on(events.CallbackQuery(data="show_price_logic"))
async def show_price_btn(event):
    await event.answer()
    await price(event)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_reply(event):
    if event.text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    reply_text = (
        "🤖 **Mr. White Official Assistant**\n\n"
        "Access today's **Correct Score Ticket** for just **$15 USD** (Available worldwide 🌍).\n\n"
        "How can I help you?"
    )
    buttons = [[Button.inline("🎫 View Ticket & Pay", data="show_start_logic")],
               [Button.inline("💰 Check $15 in My Currency", data="show_price_logic")]]
    await event.reply(reply_text, buttons=buttons)

print("Bot is running...")
client.run_until_disconnected()
