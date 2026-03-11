from telethon import TelegramClient, events, Button
import config
import database
import os

# Initialize the Client
client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

# Initialize Database
database.init_db()

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # This is the "Teaser" message shown to everyone
    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    
    welcome_text = (
        "**Welcome to Mr. White | Official Bot**\n\n"
        "💎 **NEW INFO ARRIVED**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⭐ **CONFIRMED TICKET** 🎫\n"
        "☑ **Fixed Tips:** Correct Score\n"
        "✔ **Safe:** 💯 Guaranteed\n\n"
        "To see today's full uncovered ticket, please pay via the link below and click 'Claim'."
    )

    # Sends the DAILY BLURRED teaser from Railway Variable: COVERED_TICKET_URL
    await client.send_file(
        event.chat_id, 
        config.COVERED_TICKET_URL, 
        caption=welcome_text, 
        buttons=buttons
    )

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    user = await event.get_sender()
    name = f"{user.first_name} {user.last_name or ''}"
    
    # Notify Admin (You)
    admin_buttons = [
        [Button.inline("✅ Approve", data=f"app_{user.id}"),
         Button.inline("❌ Reject", data=f"rej_{user.id}")]
    ]
    
    await client.send_message(
        config.ADMIN_ID, 
        f"🚨 **New Payment Claim!**\n\nUser: **{name}**\nUsername: @{user.username}\nID: `{user.id}`", 
        buttons=admin_buttons
    )
    await event.answer("✅ Request sent! Please wait for admin verification.", alert=True)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID:
        return
        
    data_parts = event.data.decode().split('_')
    action = data_parts[0]
    uid = int(data_parts[1])
    
    if action == "app":
        # Save to DB for 24h
        database.approve_user_24h(uid, "User")
        
        # Sends the DAILY CLEAN ticket from Railway Variable: TICKET_URL
        await client.send_file(
            uid, 
            config.TICKET_URL, 
            caption="✅ **Payment Verified!**\n\nHere is your clean uncovered ticket. Access is valid for 24 hours. Good luck!"
        )
        await event.edit(f"✅ User {uid} has been Approved.")
    else:
        await client.send_message(uid, "❌ Your payment claim was rejected. Please ensure you have paid correctly.")
        await event.edit(f"❌ User {uid} has been Rejected.")

print("Bot is running...")
client.run_until_disconnected()
