import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

# --- INITIALIZATION ---
ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = TelegramClient('ultimate_bot', config.API_ID, config.API_HASH)
current_reply_target = None
last_admin_reply = {}

# --- AI LOGIC ---
async def generate_ai_reply(user_id, message):
    history = database.get_user_memory(user_id) or ""
    prompt = f"""
You are Mr. White, a high-stakes betting consultant from Ghana.
- Tone: Confident, wealthy, and professional.
- Style: Short sentences. Use "we" to build a team feeling.
- Strategy: Remind them that "slots are limited" and "the odds won't wait."
- Local Touch: Use terms like "Momo" or "Green" for success.

History: {history}
User: {message}
AI:"""
    try:
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-2000:])
        return reply
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Checking the markets... I'll have an answer for you soon."

# --- BACKGROUND TASKS ---
async def expiry_checker():
    while True:
        try:
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT user_id FROM approved_users WHERE approved=TRUE AND expiry_time < NOW()")
            expired = cur.fetchall()
            for u in expired:
                uid = u[0]
                try: await client.send_message(uid, "⏱ Your VIP access has expired. Renew now to stay in the green!")
                except: pass
                cur.execute("UPDATE approved_users SET approved=FALSE WHERE user_id=%s", (uid,))
            conn.commit(); cur.close(); conn.close()
        except Exception as e: logger.error(f"Expiry Loop Error: {e}")
        await asyncio.sleep(60)

# --- EVENT HANDLERS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not event.is_private: return
    text = "🤝 **Welcome to the Inner Circle.**\n\nI'm Mr. White. I deal in data, not luck. VIP tips are verified daily. Ready to move?"
    buttons = [[Button.url("💳 Join VIP Now", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await event.reply(text, buttons=buttons)

@client.on(events.NewMessage())
async def handle_all(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/'): return
    
    user = await event.get_sender()
    # Log subscriber
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen=NOW()", (user.id, user.username))
    conn.commit(); cur.close(); conn.close()

    # Forward to Admin
    btn = [[Button.inline("💬 Reply", data=f"reply_{user.id}")], [Button.inline("🚫 Block", data=f"block_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"📩 **Message from {user.first_name}** (`{user.id}`)", buttons=btn)
    await client.forward_messages(config.ADMIN_ID, event.message)

    # AI Reply (if admin hasn't replied in last 2 mins)
    if user.id not in last_admin_reply or (datetime.now() - last_admin_reply[user.id]).seconds > 120:
        reply = await generate_ai_reply(user.id, event.raw_text)
        await asyncio.sleep(1.5)
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]])

@client.on(events.CallbackQuery())
async def callbacks(event):
    global current_reply_target
    data = event.data.decode()
    if data.startswith("reply_"):
        current_reply_target = int(data.split("_")[1])
        await event.answer("Type your reply now.")
    elif data == "claim_pay":
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"💰 **Payment Claim** from {user.id}", buttons=[[Button.inline("Approve 24h", data=f"app_{user.id}_{user.first_name}")]])
        await event.answer("Claim sent to admin!", alert=True)
    elif data.startswith("app_"):
        _, uid, name = data.split("_")
        database.approve_user_24h(int(uid), name)
        await client.send_message(int(uid), "✅ VIP Access Activated. Let's get to work.")
        await event.edit(f"✅ Approved {uid}")

@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_input(event):
    global current_reply_target
    if current_reply_target:
        await client.send_message(current_reply_target, f"👨‍💼 Support:\n\n{event.raw_text}")
        last_admin_reply[current_reply_target] = datetime.now()
        current_reply_target = None
        await event.reply("✅ Sent.")

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    asyncio.create_task(expiry_checker())
    print("🚀 Mr. White Bot Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())