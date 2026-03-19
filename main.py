import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

# --- INITIALIZATION ---
ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)
last_admin_reply = {}

# --- AI & SETTINGS HELPERS ---
def get_sleep_mode():
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT value FROM bot_settings WHERE key='sleep_mode'")
    row = cur.fetchone(); cur.close(); conn.close()
    return row[0] if row else False

async def generate_ai_reply(user_id, message):
    if get_sleep_mode(): return None
    history = database.get_user_memory(user_id) or ""
    prompt = f"You are Mr. White, a confident betting expert from Ghana. Be short, professional, and push for Selar sales. History: {history}\nUser: {message}\nAI:"
    try:
        res = ai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=150)
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1500:])
        return reply
    except: return None

# --- ADMIN COMMANDS (/users, /find, /sleep) ---

@client.on(events.NewMessage(pattern='/users', from_users=config.ADMIN_ID))
async def total_users(event):
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Total Bot Subscribers:** `{total}`")

@client.on(events.NewMessage(pattern='/sleep', from_users=config.ADMIN_ID))
async def toggle_sleep(event):
    mode = event.raw_text.split()[-1].lower()
    val = True if mode == "on" else False
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("UPDATE bot_settings SET value=%s WHERE key='sleep_mode'", (val,))
    conn.commit(); cur.close(); conn.close()
    await event.reply(f"😴 **Sleep Mode:** {'ON (AI Off)' if val else 'OFF (AI On)'}")

# --- CALLBACKS (Approve, Reject, Ban) ---

@client.on(events.CallbackQuery())
async def callbacks(event):
    data = event.data.decode()
    user = await event.get_sender()

    if data == "claim_pay":
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("UPDATE subscribers SET total_claims = total_claims + 1 WHERE user_id=%s", (user.id,))
        cur.execute("SELECT total_claims, rejected_claims FROM subscribers WHERE user_id=%s", (user.id,))
        stats = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}")],
                [Button.inline("❌ Reject", data=f"rej_{user.id}")],
                [Button.inline("🚫 BAN", data=f"ban_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"💰 **PAYMENT CLAIM**\nUser: {user.first_name}\nID: `{user.id}`\nStats: {stats[0]} Claims / {stats[1]} Rejections", buttons=btns)
        await event.answer("📩 Claim submitted to Mr. White.", alert=True)

    elif data.startswith("rej_"):
        uid = int(data.split("_")[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("UPDATE subscribers SET rejected_claims = rejected_claims + 1 WHERE user_id=%s", (uid,))
        conn.commit(); cur.close(); conn.close()
        await client.send_message(uid, "❌ **CLAIM REJECTED.** Verification failed. Please pay via Selar first.", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)]])
        await event.edit(f"❌ User {uid} Rejected.")

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])
        database.approve_user_24h(uid)
        await client.send_message(uid, "✅ **ACCESS GRANTED.** Use /status to check expiry.")
        await event.edit(f"✅ User {uid} Approved.")

# --- CORE MESSAGE HANDLER (AI & Alerts) ---

@client.on(events.NewMessage())
async def handle_messages(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/'): return
    
    user = await event.get_sender()
    conn = database.get_connection(); cur = conn.cursor()
    
    # 🚫 Check for Ban
    cur.execute("SELECT is_banned FROM subscribers WHERE user_id=%s", (user.id,))
    res = cur.fetchone()
    if res and res[0]: return

    # 🚨 New Visitor Alert
    if not res:
        is_p = "Yes ⭐" if getattr(user, 'premium', False) else "No"
        alert = f"🔥 **NEW VISITOR**\nName: {user.first_name}\nID: `{user.id}`\nPremium: {is_p}"
        await client.send_message(config.ADMIN_ID, alert)
        cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s)", (user.id, user.username))
    
    conn.commit(); cur.close(); conn.close()

    # Forward to Admin
    await client.send_message(config.ADMIN_ID, f"📩 **Msg from {user.first_name}** (`{user.id}`):\n{event.raw_text}")

    # 🤖 AI REPLY
    reply = await generate_ai_reply(user.id, event.raw_text)
    if reply:
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]])

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Full Vision Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
