import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)

# --- AI & SETTINGS ---
def get_sleep_mode():
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT value FROM bot_settings WHERE key='sleep_mode'")
    row = cur.fetchone(); cur.close(); conn.close()
    return row[0] if row else False

async def generate_ai_reply(user_id, message):
    if get_sleep_mode(): return None
    history = database.get_user_memory(user_id) or ""
    prompt = f"You are Mr. White, a confident betting expert from Ghana. Be short and professional. Push for Selar sales. History: {history}\nUser: {message}\nAI:"
    try:
        res = ai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=150)
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1000:])
        return reply
    except: return "The markets are moving. Check the VIP ticket for the win. 📈"

# --- COMMANDS: TICKET, SUPPORT, STATUS ---

@client.on(events.NewMessage(pattern='/ticket'))
async def send_uncovered_ticket(event):
    # Check if user is approved
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT approved FROM approved_users WHERE user_id=%s AND expiry_time > NOW()", (event.sender_id,))
    is_vip = cur.fetchone(); cur.close(); conn.close()
    
    if is_vip:
        await event.reply("💎 **YOUR UNLOCKED TICKET**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nHere is your verified info. Let's go green! 📈", file=config.TICKET_URL)
    else:
        await event.reply("❌ **ACCESS DENIED**\nYou need an active VIP subscription to view the uncovered ticket.", buttons=[[Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)]])

@client.on(events.NewMessage(pattern='/support'))
async def support(event):
    await event.reply("👨‍💻 **SUPPORT**\nContact me on WhatsApp for instant help.", buttons=[[Button.url("💬 WhatsApp", "https://wa.me/message/S3CQYVGPGOZ4H1")]])

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT expiry_time FROM approved_users WHERE user_id=%s AND expiry_time > NOW()", (event.sender_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if row:
        await event.reply(f"✅ **VIP ACTIVE**\nExpires: `{row[0].strftime('%d %b, %H:%M')}`")
    else:
        await event.reply("📉 **FREE TIER**\nNo active VIP found.")

# --- CALLBACKS: APPROVE, REJECT, BAN ---

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

    elif data.startswith("rej_"):
        uid = int(data.split("_")[1])
        await client.send_message(uid, "❌ **CLAIM REJECTED**\nWe couldn't verify your payment. Please ensure you have paid via Selar first.", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)]])
        await event.edit(f"❌ User {uid} Rejected.")

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])
        database.approve_user_24h(uid)
        await client.send_message(uid, "✅ **ACCESS GRANTED.**\nYour VIP ticket is now unlocked! Use /ticket to view.")
        await event.edit(f"✅ User {uid} Approved.")

# --- MESSAGE HANDLER: AI & FORWARDING ---

@client.on(events.NewMessage())
async def handle_messages(event):
    # 1. Skip if not private or if it's a command
    if not event.is_private or event.raw_text.startswith('/'): return
    
    # 2. Skip Admin messages (so you can use /find, /users, etc. without triggering AI)
    if event.sender_id == config.ADMIN_ID: return

    user = await event.get_sender()
    # Alert & Forward to Admin
    await client.send_message(config.ADMIN_ID, f"📩 **Msg from {user.first_name}** (`{user.id}`):\n{event.raw_text}", 
                              buttons=[[Button.inline("💬 Reply", data=f"reply_{user.id}")]])

    # 3. AI Reply
    reply = await generate_ai_reply(user.id, event.raw_text)
    if reply:
        await asyncio.sleep(1)
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]])

# --- ADMIN TOOLS ---
@client.on(events.NewMessage(pattern='/users', from_users=config.ADMIN_ID))
async def total_users(event):
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Total Subscribers:** `{total}`")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
