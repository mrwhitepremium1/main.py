from telethon import TelegramClient, events, Button
import config
import database

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)
database.init_db()

# --- 1. USER: START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    await client.send_file(
        event.chat_id, 
        config.WELCOME_IMAGE, 
        caption="**Welcome!**\n\nPay via the link above and click 'Claim' to get your ticket.",
        buttons=buttons
    )

# --- 2. USER: CLAIM BUTTON ---
@client.on(events.CallbackQuery(data=b"claim_pay"))
async def handle_claim(event):
    user = await event.get_sender()
    database.add_subscriber(user.id, user.username)
    
    # Notify Admin
    admin_buttons = [
        [Button.inline("✅ Approve", data=f"approve_{user.id}"),
         Button.inline("❌ Reject", data=f"reject_{user.id}")]
    ]
    await client.send_message(
        config.ADMIN_ID,
        f"🚨 **New Payment Claim!**\nUser: {user.first_name}\nID: `{user.id}`",
        buttons=admin_buttons
    )
    await event.edit("Verification request sent to Admin. Please wait...")

# --- 3. ADMIN: APPROVAL LOGIC ---
@client.on(events.CallbackQuery(pattern=r"(approve|reject)_(.*)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    
    decision, user_id = event.data.decode().split("_")
    user_id = int(user_id)

    if decision == "approve":
        database.update_status(user_id, 'active')
        await client.send_file(user_id, config.TICKET_IMAGE, caption="✅ **Payment Verified!** Here is today's ticket.")
        await event.edit(f"Approved user `{user_id}` and ticket sent.")
    else:
        await client.send_message(user_id, "❌ Your payment claim was rejected.")
        await event.edit(f"Rejected user `{user_id}`.")

# --- 4. ADMIN: BROADCAST SYSTEM ---
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    
    users = database.get_all_active_users()
    count = 0
    await event.respond(f"Starting broadcast to {len(users)} users...")
    
    for uid in users:
        try:
            await client.send_file(uid, config.TICKET_IMAGE, caption="📢 **New Ticket Update!**")
            count += 1
        except: continue
        
    await event.respond(f"✅ Broadcast finished. Sent to {count} users.")

client.run_until_disconnected()
