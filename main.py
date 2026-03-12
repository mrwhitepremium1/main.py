import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config, database, asyncio, time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_final_v25', config.API_ID, config.API_HASH)

# --- 1. TYPO-PROOF BROADCAST (Supports /broadcast and /boardcast) ---
@client.on(events.NewMessage(pattern=r'/(broadcast|boardcast)(.*)'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID:
        return
    msg_text = event.pattern_match.group(2).strip()
    photo = event.photo if event.photo else None
    if not msg_text and not photo:
        await event.reply("❌ **Error:** Please type a message after the command.")
        return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    if not users:
        await event.reply("❌ No subscribers found."); return
    progress_msg = await event.reply(f"📣 **Sending to {len(users)} users...**")
    success_count = 0
    for user in users:
        try:
            if photo:
                await client.send_file(user[0], photo, caption=msg_text)
            else:
                await client.send_message(user[0], msg_text)
            success_count += 1
            await asyncio.sleep(0.3)
        except Exception: continue
    await progress_msg.edit(f"✅ **Broadcast complete!** Sent to **{success_count}** users.")

# --- 2. START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user.id, user.username))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nName: {first_name}\nID: `{user.id}`\nTotal: {total}")
    cur.close(); conn.close()
    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    welcome_text = f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed\n\nTo access today's confirmed selections, please check the price via the link below and click **'I Have Paid'**."
    ts_url = f"{config.COVERED_TICKET_URL}?v={int(time.time())}"
    await client.send_file(event.chat_id, ts_url, caption=welcome_text, buttons=buttons)

# --- 3. UPDATED STATUS & SUPPORT ---
@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status: Active 🤝**\n\nYour subscription is currently active.")
    else:
        await event.reply("📊 **Status: Inactive ❌**\n\nYour subscription is currently inactive.\nPlease purchase a ticket to activate your access.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("💬 **You’re now connected to support.**\nKindly explain your issue clearly Mr. White is listening. 🎯")

# --- 4. LIVE CHAT & OFFLINE AUTO-REPLY (12AM-5AM) ---
@client.on(events.NewMessage(incoming=True))
async def forward_to_admin(event):
    if event.is_private and not event.raw_text.startswith('/') and event.sender_id != config.ADMIN_ID:
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"📩 **NEW SUPPORT MESSAGE**\n👤 **From:** {user.first_name}\n🆔 **ID:** `{event.sender_id}`\n\n💬 **Message:**\n{event.raw_text}")
        current_hour = datetime.utcnow().hour
        if 0 <= current_hour < 5:
            await event.reply("🌙 **Mr. White is currently offline.**\n\nI have received your message and will review it as soon as I am back online in the morning (after 5 AM). Thank you for your patience! 🎯")

# --- 5. ADMIN REPLY ---
@client.on(events.NewMessage(pattern=r'/reply (\d+) (.+)'))
async def admin_reply(event):
    if event.sender_id != config.ADMIN_ID: return
    user_id = int(event.pattern_match.group(1))
    reply_msg = event.pattern_match.group(2)
    try:
        await client.send_message(user_id, f"👨‍💼 **Mr. White Support:**\n\n{reply_msg}")
        await event.reply(f"✅ Reply sent to `{user_id}`")
    except Exception as e: await event.reply(f"❌ Error: {e}")

# --- 6. UPDATED BUTTON CALLBACKS (Win Guarantee & Terms) ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def wg(event):
    await event.answer()
    wg_text = "🛡️ **Mr. White Win Guarantee**\n\nWe take pride in delivering high-accuracy Correct Score selections.\nOur team conducts deep analysis and research on every match to provide carefully selected tips with a target accuracy of 95%+.\n\nOur goal is simple: consistency, transparency, and long-term trust with every subscriber."
    await event.reply(wg_text)

@client.on(events.CallbackQuery(data="terms"))
async def tr(event):
    await event.answer()
    terms_text = "⚖️ **Terms of Service**\n\n1. **Final Sale:** All purchases are final and non-refundable.\n2. **Verification:** Payment claims and access requests are subject to manual admin verification before approval.\n3. **Confidentiality:** Reselling, sharing, or redistributing tickets is strictly prohibited and may result in permanent removal."
    await event.reply(terms_text)

@client.on(events.CallbackQuery(data="claim_pay"))
async def claim(event):
    await event.answer("✅ Sent to Admin.", alert=True)
    user = await event.get_sender()
    btns = [[Button.inline("✅ Approve", data=f"app_{user.id}"), Button.inline("❌ Reject", data=f"rej_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)

# --- 7. UPDATED ADMIN ACTIONS (Verification & Rejection) ---
@client.on(events.CallbackQuery(pattern=r"(app|rej)_(\d+)"))
async def admin_decision(event):
    if event.sender_id != config.ADMIN_ID: return
    await event.answer()
    act, uid = event.data.decode().split('_')[0], int(event.data.decode().split('_')[1])
    if act == "app":
        database.approve_user_24h(uid, "User")
        approved_msg = "✅ **Payment Verified**\n\nYour payment has been successfully confirmed.\nYour ticket has been issued and will remain valid for 24 hours."
        await client.send_file(uid, config.TICKET_URL, caption=approved_msg)
        await event.edit(f"✅ Approved User {uid}")
    else:
        rejected_msg = "❌ **Payment Claim Rejected**\n\nYour payment could not be verified at this time.\nPlease contact Mr White for assistance.\n\nCommand: /support"
        await client.send_message(uid, rejected_msg)
        await event.edit(f"❌ Rejected User {uid}")

# --- 8. RUNNER ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        await client.send_message(config.ADMIN_ID, "🚀 **Bot Updated! All new professional messages are live.**")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__': asyncio.run(main())
