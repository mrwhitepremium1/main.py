import logging
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.errors import UserIsBlockedError, PeerIdInvalidError
from openai import OpenAI  # Updated for OpenAI v1.0+
import config
import database

# --- CONFIG ---
# Initialize the OpenAI client properly for the new SDK
ai_client = OpenAI(api_key=config.OPENAI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = TelegramClient('ultimate_bot', config.API_ID, config.API_HASH)

# Use a standard variable instead of attaching to the client object
current_reply_target = None
last_admin_reply = {}

# --- 🔥 HOT LEAD DETECTION ---
def is_hot_lead(msg):
    keywords = ["price", "buy", "payment", "how much", "interested", "cost", "ghana", "momo"]
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

Conversation history:
{history}

User: {message}
AI:
"""

    try:
        # Updated OpenAI completion syntax
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )

        reply = res.choices[0].message.content

        # Update memory
        new_history = (history + f"\nUser:{message}\nAI:{reply}")[-2000:]
        database.save_user_memory(user_id, new_history)

        return reply

    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        return "Thinking... one moment while I check the latest odds. 📈"

# --- ⏱ FOLLOW UP ---
async def follow_up(user_id):
    await asyncio.sleep(600) # 10 minutes
    try:
        await client.send_message(
            user_id,
            "👋 Still interested? Slots for today's VIP tips are filling fast.",
            buttons=[[Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)]]
        )
    except Exception:
        pass

# --- ⏱ EXPIRY CHECK (Fixed SQL for PostgreSQL) ---
async def expiry_checker():
    while True:
        try:
            conn = database.get_connection()
            cur = conn.cursor()

            # Fix: Use TRUE instead of 1 for PostgreSQL boolean columns
            cur.execute("SELECT user_id FROM subscribers WHERE approved=TRUE AND expiry < NOW()")
            users = cur.fetchall()

            for u in users:
                uid = u[0]
                try:
                    await client.send_message(uid, "⏱ Your VIP subscription has expired. Renew now to stay in the green!")
                except Exception:
                    pass
                # Fix: Use FALSE instead of 0
                cur.execute("UPDATE subscribers SET approved=FALSE WHERE user_id=%s", (uid,))

            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Database/Expiry Error: {e}")
        
        await asyncio.sleep(60)

# --- ADMIN REPLY ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_reply(event):
    global current_reply_target
    
    if current_reply_target:
        uid = current_reply_target
        try:
            await client.send_message(uid, f"👨‍💼 Support:\n\n{event.raw_text}")
            await event.reply(f"✅ Message sent to user {uid}")
            last_admin_reply[uid] = datetime.now()
            current_reply_target = None # Reset after sending
        except Exception as e:
            await event.reply(f"❌ Failed to send: {e}")

# --- HANDLE USERS ---
@client.on(events.NewMessage())
async def handle(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID:
        return

    if event.raw_text.startswith('/'):
        return

    user = await event.get_sender()
    
    # SAVE/UPDATE USER IN DB
    try:
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO subscribers (user_id, username, last_seen)
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET last_seen=%s, username=%s
        """, (user.id, user.username, datetime.now(), datetime.now(), user.username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB Update Error: {e}")

    # HOT LEAD LOGIC
    if is_hot_lead(event.raw_text):
        database.mark_hot_lead(user.id)

    # FORWARD TO ADMIN
    buttons = [
        [Button.inline("💬 Reply", data=f"reply_{user.id}")],
        [Button.inline("🚫 Block", data=f"block_{user.id}")]
    ]

    await client.send_message(
        config.ADMIN_ID,
        f"📩 **New Message**\nUser: {user.first_name}\nID: `{user.id}`",
        buttons=buttons
    )
    await client.forward_messages(config.ADMIN_ID, event.message)

    # QUEUE FOLLOW UP
    asyncio.create_task(follow_up(user.id))

    # SILENCE AI IF ADMIN REPLIED RECENTLY (2-minute window)
    if user.id in last_admin_reply:
        if (datetime.now() - last_admin_reply[user.id]).seconds < 120:
            return

    # GENERATE AI REPLY
    reply = await generate_ai_reply(user.id, event.raw_text)
    await asyncio.sleep(1.5) # Realistic typing delay

    await event.reply(
        f"🤖 {reply}",
        buttons=[
            [Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]
        ]
    )

# --- CALLBACKS ---
@client.on(events.CallbackQuery())
async def callbacks(event):
    global current_reply_target
    data = event.data.decode()

    if data.startswith("reply_"):
        current_reply_target = int(data.split("_")[1])
        await event.answer("Type your reply to the user now.")

    elif data.startswith("block_"):
        uid = int(data.split("_")[1])
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id=%s", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        await event.edit("🚫 User removed from database.")

    elif data == "claim_pay":
        user = await event.get_sender()
        await client.send_message(
            config.ADMIN_ID,
            f"💰 **Payment Claim!**\nUser: {user.first_name}\nID: `{user.id}`",
            buttons=[[Button.inline("✅ Approve 24h", data=f"app_{user.id}")]]
        )
        await event.answer("Payment claim sent to admin!", alert=True)

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])
        database.approve_user_24h(uid) # Ensure this function uses TRUE/FALSE internally
        await client.send_message(uid, "✅ Your payment has been confirmed. You now have 24h VIP access!")
        await event.edit(f"✅ User {uid} approved.")

# --- ADMIN COMMANDS ---
@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id != config.ADMIN_ID: return
    
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
    # Fix: Use TRUE
    cur.execute("SELECT COUNT(*) FROM subscribers WHERE is_hot=TRUE")
    hot = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    await event.reply(f"📊 **Bot Stats**\nTotal Users: {total}\nHot Leads: {hot}")

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    
    # Start the background task
    asyncio.create_task(expiry_checker())

    print("🚀 Ultimate Bot Running Successfully")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
