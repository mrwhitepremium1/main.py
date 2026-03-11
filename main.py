from telethon import TelegramClient, events, Button
import config
import database

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

# Initialize database on startup
database.init_db()

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    await client.send_file(
        event.chat_id, 
        config.WELCOME_IMAGE, 
        caption="**Welcome to Mr. White Official!**\n\nTo get today's ticket, please pay using the link below and then click 'Claim'.", 
        buttons=buttons
    )

@client.on(events.CallbackQuery(pattern=b"claim_pay"))
async def handle_claim(event):
    # Stop the loading spinner on user's phone
    await event.answer("Verification request sent!", alert=True)
    
    user = await event.get_sender()
    username = user.username if user.username else user.first_name
    
    # Create buttons for the ADMIN to click
    admin_buttons = [
        [Button.inline("✅ Approve", data=f"app_{user.id}"), 
         Button.inline("❌ Reject", data=f"rej_{user.id}")]
    ]
    
    # Send notification to the ADMIN
    await client.send_message(
        config.ADMIN_ID, 
        f"🚨 **New Payment Claim!**\n\nUser: {user.first_name}\nUsername: @{user.username}\nID: `{user.id}`", 
        buttons=admin_buttons
    )
    
    await event.edit("✅ Your request has been sent to the Admin. Please wait for verification.")

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(.*)"))
async def admin_decision(event):
    # Only the Admin can click these buttons
    if event.sender_id != config.ADMIN_ID:
        await event.answer("Access Denied.", alert=True)
        return

    data = event.data.decode().split("_")
    action = data[0]
    uid = int(data[1])

    if action == "app":
        # 1. Update database for 24 hours
        database.approve_user_24h(uid, "User")
        
        # 2. Send the ticket to the user
        await client.send_file(uid, config.TICKET_IMAGE, caption="✅ **Payment Verified!**\n\nHere is your ticket. It is valid for 24 hours.")
        
        # 3. Update the admin's view
        await event.edit(f"✅ User `{uid}` Approved. Ticket sent.")
        
    elif action == "rej":
        await client.send_message(uid, "❌ **Payment Rejected.**\n\nPlease ensure you have completed the payment before claiming.")
        await event.edit(f"❌ User `{uid}` Rejected.")

client.run_until_disconnected()
