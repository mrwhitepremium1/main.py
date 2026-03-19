import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

# --- SETUP ---
ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)
current_reply_target = None
last_admin_reply = {}

# --- AI CORE (Mr. White Persona) ---
async def generate_ai_reply(user_id, message):
    history = database.get_user_memory(user_id) or ""
    prompt = f"You are Mr. White, a wealthy, confident betting expert from Ghana. Be short, human, and professional. Use 'Momo' and 'Green' terminology. History: {history}\nUser: {message}\nAI:"
    try:
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1500:])
        return reply
    except Exception as e:
        print(f"AI ERROR: {e}")
        return "Analyzing the markets... the green is coming. 📈"

# --- HANDLERS ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    welcome = (
        "Hello 👋 **Mr White!**\n\n"
        "**Welcome to Mr. White | Official Bot**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "💎 **PREMIUM INFO ARRIVED**\n"
        "⭐ **CONFIRMED TICKET** 🎫\n\n"
        "☑️ **Fixed Tips:** Correct Score\n"
        "✔️ **Verification:** 100% Guaranteed\n\n"
        "Check the price via the link below and click 'I Have Paid'."
    )
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await event.reply(welcome, file=config.COVERED_TICKET_URL, buttons=btns)

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
    cur.close(); conn.close()
    
    status = await event.reply(f"🚀 Sending to {len(users)} users...")
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    count = 0
    for u in users:
        try:
            msg = await client.send_message(u[0], "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nLast call for tonight's winners. Secure your spot now!", file=config.COVERED_TICKET_URL, buttons=btns)
            await client.pin_message(u[0], msg.id, notify=True)
            count += 1
            await asyncio.sleep(0.2)
        except: continue
    await status.edit(f"✅ Sent and Pinned for {count} users.")

@client.on(events.NewMessage())
async def handle_messages(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/'): return
    
    user = await event.get_sender()
    # Log user
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (user.id, user.username))
    conn.commit(); cur.close(); conn.close()

    # Forward to Admin
    await client.send_message(config.ADMIN_ID, f"📩 **Message from {user.first_name}** (`{user.id}`)", buttons=[[Button.inline("💬 Reply", data=f"reply_{user.id}")]])
    await client.forward_messages(config.ADMIN_ID, event.message)

    # AI Response
    if user.id not in last_admin_reply or (datetime.now() - last_admin_reply[user.id]).seconds > 120:
        reply = await generate_ai_reply(user.id, event.raw_text)
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]])

# --- MAIN ---
async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Bot Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
