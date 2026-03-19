import logging
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.errors import UserIsBlockedError, PeerIdInvalidError
import openai
import config
import database

# --- CONFIG ---
openai.api_key = config.OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

client = TelegramClient('ultimate_bot', config.API_ID, config.API_HASH)

sleep_mode_active = False
client.reply_target = None
last_admin_reply = {}

# --- 🔥 HOT LEAD DETECTION ---
def is_hot_lead(msg):
    keywords = ["price", "buy", "payment", "how much", "interested"]
    return any(k in msg.lower() for k in keywords)

# --- 🧠 AI MEMORY ---
async def generate_ai_reply(user_id, message):
    history = database.get_user_memory(user_id)

    prompt = f"""
You are Mr. White, a confident Telegram betting expert.

- Be short, human-like
- Build trust
- Gently push to buy
- Create urgency

Conversation:
{history}

User: {message}
AI:
"""

    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )

        reply = res.choices[0].message["content"]

        new_history = (history + f"\nUser:{message}\nAI:{reply}")[-2000:]
        database.save_user_memory(user_id, new_history)

        return reply

    except:
        return "🤖 Please wait, support will reply."

# --- ⏱ FOLLOW UP ---
async def follow_up(user_id):
    await asyncio.sleep(600)

    try:
        await client.send_message(
            user_id,
            "👋 Still interested? Slots are filling fast.",
            buttons=[[Button.url("💳 Buy Now", config.SELAR_PAYMENT_LINK)]]
        )
    except:
        pass

# --- ⏱ EXPIRY CHECK ---
async def expiry_checker():
    while True:
        conn = database.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT user_id FROM subscribers WHERE approved=1 AND expiry < NOW()")
        users = cur.fetchall()

        for u in users:
            uid = u[0]
            await client.send_message(uid, "⏱ Subscription expired.")
            cur.execute("UPDATE subscribers SET approved=0 WHERE user_id=%s", (uid,))

        conn.commit()
        cur.close()
        conn.close()

        await asyncio.sleep(60)

# --- ADMIN REPLY ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_reply(event):
    if client.reply_target:
        uid = client.reply_target

        await client.send_message(uid, f"👨‍💼 Support:\n\n{event.raw_text}")
        await event.reply(f"✅ Sent to {uid}")

        last_admin_reply[uid] = datetime.now()
        client.reply_target = None

# --- HANDLE USERS ---
@client.on(events.NewMessage())
async def handle(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID:
        return

    if event.raw_text.startswith('/'):
        return

    # BLOCK CHECK
    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM subscribers WHERE user_id=%s", (event.sender_id,))
    if not cur.fetchone():
        return

    cur.close()
    conn.close()

    # SAVE USER
    user = await event.get_sender()

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO subscribers (user_id, username, last_seen)
        VALUES (%s,%s,%s)
        ON CONFLICT (user_id) DO UPDATE SET last_seen=%s
    """, (user.id, user.username, datetime.now(), datetime.now()))

    conn.commit()
    cur.close()
    conn.close()

    # HOT LEAD
    if is_hot_lead(event.raw_text):
        database.mark_hot_lead(user.id)

    # FORWARD TO ADMIN WITH BUTTONS
    buttons = [
        [Button.inline("💬 Reply", data=f"reply_{user.id}")],
        [Button.inline("🚫 Block", data=f"block_{user.id}")]
    ]

    await client.send_message(
        config.ADMIN_ID,
        f"📩 {user.first_name}\nID: `{user.id}`",
        buttons=buttons
    )

    await client.forward_messages(config.ADMIN_ID, event.message)

    # FOLLOW UP
    client.loop.create_task(follow_up(user.id))

    # AI CONTROL
    if user.id in last_admin_reply:
        diff = (datetime.now() - last_admin_reply[user.id]).seconds
        if diff < 120:
            return

    # AI REPLY
    reply = await generate_ai_reply(user.id, event.raw_text)

    await asyncio.sleep(2)

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
    data = event.data.decode()

    if data.startswith("reply_"):
        client.reply_target = int(data.split("_")[1])
        await event.answer("Send reply now")

    elif data.startswith("block_"):
        uid = int(data.split("_")[1])

        conn = database.get_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM subscribers WHERE user_id=%s", (uid,))
        conn.commit()

        cur.close()
        conn.close()

        await event.edit("🚫 User blocked")

    elif data == "claim_pay":
        user = await event.get_sender()

        await client.send_message(
            config.ADMIN_ID,
            f"Payment claim from {user.id}",
            buttons=[[Button.inline("Approve", data=f"app_{user.id}")]]
        )

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])

        database.approve_user_24h(uid)

        await client.send_message(uid, "✅ Approved (24h access)")

# --- STATS ---
@client.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id != config.ADMIN_ID:
        return

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM subscribers WHERE is_hot=1")
    hot = cur.fetchone()[0]

    cur.close()
    conn.close()

    await event.reply(f"Users: {total}\nHot Leads: {hot}")

# --- HOT LIST ---
@client.on(events.NewMessage(pattern='/hot'))
async def hot(event):
    if event.sender_id != config.ADMIN_ID:
        return

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM subscribers WHERE is_hot=1 LIMIT 20")
    users = cur.fetchall()

    msg = "🔥 Hot Leads:\n"
    for u in users:
        msg += f"{u[0]}\n"

    await event.reply(msg)

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)

    client.loop.create_task(expiry_checker())

    print("🚀 Ultimate Bot Running")
    await client.run_until_disconnected()

asyncio.run(main())