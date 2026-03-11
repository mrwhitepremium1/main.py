from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
import config
import database
import os

client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# --- 1. START & STATUS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "Winner"
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers WHERE user_id = %s", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
        conn.commit()
    cur.close(); conn.close()

    buttons = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("🛡️ Win Guarantee", data="win_guarantee"), Button.inline("⚖️ Terms", data="terms")],
        [Button.inline("❓ How to Pay", data="how_to_pay"), Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    
    welcome_text = f"""Hello 👋 {first_name}!

**Welcome to Mr. White | Official Bot**

💎 **NEW INFO ARRIVED**
━━━━━━━━━━━━━━━━━━━
⭐ **CONFIRMED TICKET** 🎫
☑ **Fixed Tips:** Correct Score
✔ **Safe:** 💯 Guaranteed

To see today's full ticket, please check the price and buy your ticket via the link below, then click 'Claim'."""
    
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if database.is_user_approved(event.sender_id):
        await event.reply("📊 **Status:** Your access is **ACTIVE**. You have full access to current tickets.")
    else:
        await event.reply("📊 **Status:** Your access is currently **INACTIVE**. Please purchase a ticket to activate.")

@client.on(events.NewMessage(pattern='/support'))
async def support_cmd(event):
    await event.reply("👋 **Support:** Contact @Best_Admin24 for assistance.")

# --- 2. THE BROADCAST COMMAND (Fixed) ---
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_cmd(event):
    if event.sender_id != config.ADMIN_ID:
        return
    
    # Get the message after the /broadcast command
    msg_to_send = event.text.replace('/broadcast', '').strip()
    if not msg_to_send:
        return await event.reply("❌ **Usage:** `/broadcast [your message here]`")
    
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    count = 0
    await event.reply(f"🚀 **Starting broadcast to {len(users)} users...**")
    
    for u in users:
        try:
            await client.send_message(u[0], msg_to_send)
            count += 1
            await asyncio.sleep(0.05) # Prevent spam limits
        except Exception:
            continue
            
    await event.reply(f"✅ **Broadcast Finished!** Sent to {count} users.")

# --- 3. RANDOM MESSAGE / ASSISTANT (Fixed) ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def random_message_assistant(event):
    # Only trigger if it's NOT a command and NOT the admin
    if event.text.startswith('/') or event.sender_id == config.ADMIN_ID:
        return

    # This catches random text and offers help
    assist_buttons = [[Button.inline("🎫 View Today's Ticket", data="trigger_start")]]
    await event.reply("🤖 **Mr. White Assistant:** It looks like you're looking for information. Would you like to view today's ticket details?", buttons=assist_buttons)

@client.on(events.CallbackQuery(data="trigger_start"))
async def cb_trigger_start(event):
    await event.answer()
    await start(event)

# --- 4. INFORMATION & ADMIN CALLBACKS ---
@client.on(events.CallbackQuery(data="win_guarantee"))
async def win_guarantee_handler(event):
    await event.answer() 
    await event.reply("🛡️ **Mr. White Win Guarantee**\n\nWe provide high-accuracy Correct Score selections with a 95%+ success rate.")

@client.on(events.CallbackQuery(data="terms"))
async def terms_handler(event):
    await event.answer()
    await event.reply("⚖️ **Terms of Service**\n\n1. All sales final.\n2. Claims verified manually.\n3. No reselling.")

@client.on(events.CallbackQuery(data="how_to_pay"))
async def how_to_pay_handler(event):
    await event.answer()
    await event.reply("📖 **How to Pay:** Click the link, choose your currency, pay, and then click 'Claim'.")

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
    data = event.data.decode().split('_')
    action, uid = data[0], int(data[1])
    
    if action == "app":
        database.approve_user_24h(uid, "User")
        await client.send_file(uid, config.TICKET_URL, caption="✅ **Payment Verified!** Your ticket is valid for 24 hours.")
        await event.edit(f"✅ User {uid} Approved.")
    else:
        await client.send_message(uid, "❌ **Payment Rejected.** Contact @Best_Admin24.")
        await event.edit(f"❌ User {uid} Rejected.")

# --- 5. RUN ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        database.init_db()
        print("✅ Bot is online with Broadcast and Assistant enabled.")
        await client.run_until_disconnected()
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds); await main()

if __name__ == '__main__':
    asyncio.run(main())
