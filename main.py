import logging
from telethon import TelegramClient, events, Button
import config, database, asyncio

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v4_session', config.API_ID, config.API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    # Database Logic
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM subscribers")
        total = cur.fetchone()[0]
        await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`\nTotal Users: {total}")
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, 
                           caption=f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n\nTo see today's ticket, check the price via the link below and click 'Claim'.", 
                           buttons=buttons)

# --- FIXED STATUS COMMAND ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE** ✅\nYou have full access to current tickets.")
    else:
        await event.reply("📊 **Status:** Your access is **INACTIVE** ❌\nPlease purchase a ticket to activate your access.")

# --- BROADCAST & CALLBACKS (Requested Messages) ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    await event.reply("🛡️ **Mr. White Win Guarantee**\n\nWe provide high-accuracy Correct Score selections with a **95%+ success rate**.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    await event.reply("⚖️ **Terms of Service**\n\n1. Final Sale: No refunds.\n2. No Reselling: Account will be banned.")

@client.on(events.CallbackQuery(data="how_to_pay"))
async def htp(event):
    await event.answer()
    await event.reply("📖 **How to Pay:** Click link > Select Currency > Pay > Return and click 'I Have Paid'.")

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
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if act == "app":
        database.approve_user_24h(uid, "User")
        msg = "✅ **Payment Verified**\n\nYour ticket has been successfully issued and is valid for 24 hours."
        await client.send_file(uid, config.TICKET_URL, caption=msg)
        await event.edit(f"✅ Approved {uid}")
    else:
        msg = "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Contact @Best_Admin24."
        await client.send_message(uid, msg)
        await event.edit(f"❌ Rejected {uid}")

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    database.init_db()
    await client.send_message(config.ADMIN_ID, "🚀 Bot is Online & Status Fixed!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
