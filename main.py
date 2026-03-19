import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)

# --- HELPERS ---
def get_sleep_mode():
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT value FROM bot_settings WHERE key='sleep_mode'")
    row = cur.fetchone(); cur.close(); conn.close()
    return row[0] if row else False

# --- THE MESSAGE HANDLER (ANTI-LOOP FIX) ---
@client.on(events.NewMessage())
async def handle_messages(event):
    # 1. STOP THE LOOP: Don't reply to Admin or Commands
    if not event.is_private or event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/'):
        return
    
    user = await event.get_sender()
    conn = database.get_connection(); cur = conn.cursor()
    
    # 2. BAN CHECK
    cur.execute("SELECT is_banned FROM subscribers WHERE user_id=%s", (user.id,))
    res = cur.fetchone()
    if res and res[0]: return # Silence for banned users

    # 3. NEW VISITOR ALERT (Log & Notify Admin)
    if not res:
        is_p = "Yes ⭐" if getattr(user, 'premium', False) else "No"
        alert = f"🔥 **NEW VISITOR ALERT**\n👤 {user.first_name}\n🆔 `{user.id}`\n⭐ Premium: {is_p}"
        await client.send_message(config.ADMIN_ID, alert)
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
    
    conn.commit(); cur.close(); conn.close()

    # 4. FORWARD TO ADMIN (One-way only)
    await client.send_message(config.ADMIN_ID, f"📩 **Msg from {user.first_name}** (`{user.id}`):\n{event.raw_text}", 
                              buttons=[[Button.inline("💬 Reply", data=f"reply_{user.id}")]])

    # 5. AI AUTO-REPLY
    if not get_sleep_mode():
        reply = await generate_ai_reply(user.id, event.raw_text)
        if reply:
            await event.reply(f"🤖 {reply}", buttons=[
                [Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)],
                [Button.inline("✅ I Have Paid", data="claim_pay")]
            ])

# --- ADMIN ACTIONS (Callbacks) ---
@client.on(events.CallbackQuery())
async def callbacks(event):
    data = event.data.decode()
    
    if data == "claim_pay":
        user = await event.get_sender()
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}")],
                [Button.inline("❌ Reject", data=f"rej_{user.id}")],
                [Button.inline("🚫 BAN", data=f"ban_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"💰 **PAYMENT CLAIM**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)
        await event.answer("📩 Verification sent to Mr. White.", alert=True)

    elif data.startswith("ban_"):
        uid = int(data.split("_")[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("UPDATE subscribers SET is_banned=TRUE WHERE user_id=%s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit(f"🚫 User {uid} has been BANNED.")

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])
        database.approve_user_24h(uid)
        await client.send_message(uid, "✅ **ACCESS GRANTED.**\nYour VIP ticket is now unlocked.")
        await event.edit(f"✅ Approved {uid}")

# --- START COMMAND (Official Look) ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id == config.ADMIN_ID:
        await event.reply("Admin Mode: Active. Commands: /users, /sleep, /broadcast")
        return

    welcome = (
        "Hello 👋 **Mr White!**\n\n"
        "**Welcome to Mr. White | Official Bot**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "💎 **PREMIUM INFO ARRIVED**\n"
        "⭐ **CONFIRMED TICKET** 🎫\n\n"
        "☑️ **Fixed Tips:** Correct Score\n"
        "✔️ **Verification:** 100% Guaranteed\n\n"
        "To access today's confirmed selections, please check the price via the link below and click 'I Have Paid'."
    )
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await event.reply(welcome, file=config.COVERED_TICKET_URL, buttons=btns)

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Professional Edition Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
