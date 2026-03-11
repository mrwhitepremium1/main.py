from telethon import TelegramClient, events, Button
import config
import database
import os

# Initialize the Client
client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

# Initialize Database
database.init_db()

# --- BROADCAST COMMAND (Admin Only) ---
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID:
        return
    
    msg_text = event.text.replace('/broadcast', '').strip()
    if not msg_text:
        await event.reply("❌ Please provide a message. Example: `/broadcast Hello!`")
        return

    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    users = cur.fetchall()
    cur.close()
    conn.close()

    count = 0
    await event.reply(f"🚀 Sending broadcast to {len(users)} users...")
    for user in users:
        try:
            await client.send_message(user[0], msg_text)
            count += 1
        except:
            continue
    await event.reply(f"✅ Broadcast complete! Sent to {count} users.")

# --- START COMMAND (Personalized + Visitor Alert) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "there"
    
    # Save user to DB and check if they are new
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    existing_user = cur.fetchone()
    
    if not existing_user:
        # Add new user to DB
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        
        # Count total users for the alert
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total_users = cur.fetchone()[0]
        
        # Notify Admin of NEW visitor
        visitor_alert = (
            "👤 **New Visitor Alert!**\n\n"
            f"**Name:** {first_name}\n"
            f"**Username:** @{user.username if user.username else 'N/A'}\n"
            f"**ID:** `{user.id}`\n\n"
            f"📈 **Total Users:** {total_users}"
        )
        await client.send_message(config.ADMIN_ID, visitor_alert)

    cur.close()
    conn.close()

    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    
    welcome_text = (
        f"Hello 👋 {first_name}!\n\n"
        "**Welcome to Mr. White | Official Bot**\n\n"
        "💎 **NEW INFO ARRIVED**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⭐ **CONFIRMED TICKET** 🎫\n"
        "☑ **Fixed Tips:** Correct Score\n"
        "✔ **Safe:** 💯 Guaranteed\n\n"
        "To see today's full uncovered ticket, please pay via the link below and click 'Claim'."
    )

    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- CLAIM BUTTON ---
@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    user = await event.get_sender()
    name = f"{user.first_name} {user.last_name or ''}"
    admin_buttons = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Payment Claim!**\n\nUser: **{name}**\nUsername: @{user.username}", buttons=admin_buttons)
    await event.answer("✅ Request sent! Please wait for admin verification.", alert=True)

# --- ADMIN DECISION ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    action, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        success_caption = (
            "✅ **Payment Verified**\n\n"
            "Your ticket has been successfully issued and is valid for 24 hours.\n\n"
            "For any issues or inquiries, please contact: @Best_Admin24"
        )
        await client.send_file(uid, config.TICKET_URL, caption=success_caption)
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ Your payment claim was rejected.")
        await event.edit(f"❌ User {uid} Rejected.")

print("Bot is running...")
client.run_until_disconnected()
