from telethon import TelegramClient, events, Button
import config
import database

client = TelegramClient('bot_session', config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)
database.init_db()

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.url("💳 Pay via Selar", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid (Claim)", data="claim_pay")]
    ]
    await client.send_file(event.chat_id, config.WELCOME_IMAGE, caption="**Welcome!**\n\nPay and then click 'Claim'.", buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"claim_pay"))
async def handle_claim(event):
    user = await event.get_sender()
    admin_buttons = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=admin_buttons)
    await event.edit("Sent to Admin. Please wait...")

@client.on(events.CallbackQuery(pattern=r"(app|rej)_(.*)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    action, uid = event.data.decode().split("_")
    uid = int(uid)

    if action == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_IMAGE, caption="✅ **Verified!** Here is today's ticket.")
        await event.edit(f"✅ Approved {uid}. Ticket sent.")
    else:
        await client.send_message(uid, "❌ Rejected.")
        await event.edit(f"❌ Rejected {uid}.")

client.run_until_disconnected()
