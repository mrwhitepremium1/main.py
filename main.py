from telethon import TelegramClient, events, Button
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

database.init_db()

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    # Sends the DAILY BLURRED teaser from Railway
    await client.send_file(
        event.chat_id, 
        config.COVERED_TICKET_URL, 
        caption="**Welcome to Mr. White Official!**\n\nTo see today's full uncovered ticket, please pay via the link below and click 'Claim'.", 
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
    await event.answer("Wait for admin approval...", alert=True)

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID:
        return
        
    action = event.data.decode().split('_')[0]
    uid = int(event.data.decode().split('_')[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        # Sends the DAILY CLEAN ticket from Railway
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!**\n\nHere is your ticket. It is valid for 24 hours.")
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ Your payment claim was rejected. Please contact support.")
        await event.edit(f"❌ User {uid} Rejected.")

print("Bot is running...")
client.run_until_disconnected()
