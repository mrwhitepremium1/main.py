from telethon import TelegramClient, events, Button
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)
database.init_db()

# --- START COMMAND ---
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
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\n\nName: {first_name}\nUsername: @{user.username}\n📈 Total Users: {total}")
    cur.close(); conn.close()

    buttons = [[Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
               [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\n"
                    "💎 **NEW INFO ARRIVED**\n━━━━━━━━━━━━━━━━━━━\n"
                    "⭐ **CONFIRMED TICKET** 🎫\n☑ **Fixed Tips:** Correct Score\n✔ **Safe:** 💯 Guaranteed\n\n"
                    "To see today's full uncovered ticket, please pay via the link and click 'Claim'.")
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- MENU COMMANDS ---
@client.on(events.NewMessage(pattern='/support'))
async def support(event):
    await event.reply("👋 **Need help?**\n\nContact our official admin: @Best_Admin24")

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("✅ **Active:** You have full access for 24 hours.")
    else:
        await event.reply("❌ **Inactive:** No active ticket found. Use /start to buy.")

# --- BROADCAST (Admin Only) ---
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

# --- CLAIM & ADMIN DECISION ---
@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)
    await event.answer("✅ Request sent to Admin.", alert=True)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    action, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        cap = "✅ **Payment Verified**\n\nYour ticket is issued (24h valid).\nContact: @Best_Admin24"
        await client.send_file(uid, config.TICKET_URL, caption=cap)
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Claim Rejected**\nPlease check details or contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

# --- NEW: AUTO-REPLY FOR ALL OTHER MESSAGES ---
@client.on(events.NewMessage)
async def auto_reply(event):
    # Don't reply to commands or the bot's own messages
    if event.text.startswith('/') or event.is_bot:
        return
    
    # Don't reply to the Admin (you) so you can still type commands
    if event.sender_id == config.ADMIN_ID:
        return

    reply_text = (
        "🤖 **Mr. White Official Assistant**\n\n"
        "I am an automated system. To view today's winning ticket or make a payment, "
        "please click the button below or type **/start**.\n\n"
        "For direct chat with an agent, contact: @Best_Admin24"
    )
    
    buttons = [Button.inline("🎫 View Ticket", data="show_start_logic")]
    await event.reply(reply_text, buttons=buttons)

# Small helper to make the "View Ticket" button work in the auto-reply
@client.on(events.CallbackQuery(data="show_start_logic"))
async def show_start(event):
    await start(event)

print("Bot is running...")
client.run_until_disconnected()
