import logging
from telethon import TelegramClient, events, Button
import config, database, asyncio

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_strict_v11', config.API_ID, config.API_HASH)

# --- 1. START & NEW USER ALERT ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
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
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = f"""Hello 👋 {first_name}!

**Welcome to Mr. White | Official Bot**
━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM INFO ARRIVED**
⭐ **CONFIRMED TICKET** 🎫

☑ **Fixed Tips:** Correct Score
✔ **Verification:** 100% Guaranteed

To access today's confirmed selections, please check the price via the link below and click **'I Have Paid'**."""

    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

# --- 2. STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    # STRICT CHECK: Result from approved_users table only
    is_active = database.is_user_approved(event.sender_id)
    
    if is_active:
        await event.reply("📊 **Status: ACTIVE** ✅")
    else:
        await event.reply("📊 **Status: INACTIVE** ❌")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- 3. CALLBACKS & ADMIN DECISION ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer(); await event.reply("🛡️ **Mr. White Win Guarantee**\n\n95%+ Accuracy Guaranteed through expert analysis.")

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer(); await event.reply("⚖️ **Terms of Service**\n\n1. Final Sale.\n2. Manual Verification.\n3. Reselling is prohibited.")

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
        await event.edit(f"✅ Approved User {uid}")
    else:
        msg = "❌ **Payment Claim Rejected**\n\nYour payment could not be verified. Please check your payment details and try again or contact @Best_Admin24."
        await client.send_message(uid, msg)
        await event.edit(f"❌ Rejected User {uid}")

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    database.init_db()
    await client.send_message(config.ADMIN_ID, "🚀 **Bot Online - Status Logic Fully Reset!**")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
