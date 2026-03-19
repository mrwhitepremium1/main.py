import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

# --- CONFIG ---
ai_client = OpenAI(api_key=config.OPENAI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = TelegramClient('ultimate_bot', config.API_ID, config.API_HASH)

current_reply_target = None
last_admin_reply = {}

# --- 🔥 HOT LEAD DETECTION ---
def is_hot_lead(msg):
    keywords = ["price", "buy", "payment", "how much", "interested", "cost", "momo", "ghana"]
    return any(k in msg.lower() for k in keywords)

# --- 🧠 AI MEMORY ---
async def generate_ai_reply(user_id, message):
    history = database.get_user_memory(user_id) or ""
    prompt = f"""
You are Mr. White, a confident Telegram betting expert.
- Be short, human-like.
- Build trust.
- Gently push to buy.
- Create urgency.

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
        new_history = (history + f"\nUser:{message}\nAI:{reply}")[-2000:]
        database.save_user_memory(user_id, new_history)
        return reply
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Checking the latest tips... stay tuned. 📈"

# --- ⏱ FOLLOW UP ---
async def follow_up(user_id):
    await asyncio.sleep(600)
    try:
        await client.send_message(
            user_id,
            "👋 Still interested? VIP slots for today are nearly full.",
            buttons=[[Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)]]
        )
    except:
        pass

# --- ⏱ EXPIRY CHECK (Fixed for approved_users table) ---
async def expiry_checker():
    while True:
        try:
            conn = database.get_connection()
            cur = conn.cursor()
            # Points to the correct table and column names from your database.py
            cur.execute("SELECT user_id FROM approved_users WHERE approved=TRUE AND expiry_time < NOW()")
            expired_users = cur.fetchall()

            for u in expired_users:
                uid = u[0]
                try:
                    await client.send_message(uid, "⏱ Your VIP access has expired. Renew now to continue winning!")
                except:
                    pass
                cur.execute("UPDATE approved_users SET approved=FALSE WHERE user_id=%s", (uid,))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Expiry Loop Error: {e}")
        
        await asyncio.sleep(60)

# --- ADMIN REPLY ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_reply(event):
    global current_reply_target
    if current_reply_target:
        try:
            await client.send_message(current_reply_target, f"👨‍💼 Support:\n\n{event.raw_text}")
            await event.reply(f"✅ Sent to {current_reply_target}")
            last_admin_reply[current_reply_target] = datetime.now()
            current_reply_target = None
        except Exception as e:
            await event.reply(f"❌ Error: {e}")

# --- HANDLE USERS ---
@client.on(events.NewMessage())
async def handle(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID:
        return
    if event.raw_text.startswith('/'):
        return

    user = await event.get_sender()

    # Track user in subscribers table
    try:
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO subscribers (user_id, username, last_seen)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET last_seen=NOW(), username=EXCLUDED.username
        """, (user.id, user.username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Subscriber Update Error: {e}")

    if is_hot_lead(event.raw_text):
        database.mark_hot_lead(user.id)

    # Notify Admin
    buttons = [
        [Button.inline("💬 Reply", data=f"reply_{user.id}")],
        [Button.inline("🚫 Block", data=f"block_{user.id}")]
    ]
    await client.send_message(config.ADMIN_ID, f"📩 **Message from {user.first_name}** (`{user.id}`)", buttons=buttons)
    await client.forward_messages(config.ADMIN_ID, event.message)

    asyncio.create_task(follow_up(user.id))

    # AI Logic
    if user.id in last_admin_reply:
        if (datetime.now() - last_admin_reply[user.id]).seconds < 120:
            return

    reply = await generate_ai_reply(user.id, event.raw_text)
    await asyncio.sleep(1.5)
    await event.reply(f"🤖 {reply}", buttons=[
        [Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ])

# --- CALLBACKS ---
@client.on(events.CallbackQuery())
async def callbacks(event):
    global current_reply_target
    data = event.data.decode()

    if data.startswith("reply_"):
        current_reply_target = int(data.split("_")[1])
        await event.answer("Type your reply to the user.")

    elif data.startswith("block_"):
        uid = int(data.split("_")[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id=%s", (uid,))
        cur.execute("DELETE FROM approved_users WHERE user_id=%s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await event.edit("🚫 User blocked and removed.")

    elif data == "claim_pay":
        user = await event.get_sender()
        await client.send_message(config.ADMIN_ID, f"💰 **Payment Claim** from `{user.id}`", 
                                  buttons=[[Button.inline("Approve 24h", data=f"app_{user.id}_{user.first_name}")]])
        await event.answer("Claim sent to admin!", alert=True)

    elif data.startswith("app_"):
        parts = data.split("_")
        uid = int(parts[1])
        name = parts[2]
        database.approve_user_24h(uid, name)
        await client.send_message(uid, "✅ Your payment is confirmed! 24h VIP access granted.")
        await event.edit(f"✅ Approved {uid}")

# --- ADMIN COMMANDS ---
@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM subscribers WHERE is_hot=TRUE")
    hot = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Stats**\nTotal: {total}\nHot: {hot}")

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    asyncio.create_task(expiry_checker())
    print("🚀 Ultimate Bot Running Successfully")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
