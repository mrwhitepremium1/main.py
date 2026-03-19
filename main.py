import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)

# --- AI LOGIC ---
async def generate_ai_reply(user_id, message):
    if database.get_sleep_mode(): return None
    history = database.get_user_memory(user_id) or ""
    prompt = f"You are Mr. White, a betting expert. Be professional, short, and push for Selar sales. History: {history}\nUser: {message}"
    try:
        res = ai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=150)
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1000:])
        return reply
    except: return "The green is coming. Check the VIP link for the verified ticket. 📈"

# --- COMMANDS (Always Works) ---
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
        "Check the price below and click 'I Have Paid' once done."
    )
    btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    await event.reply(welcome, file=config.COVERED_TICKET_URL, buttons=btns)

@client.on(events.NewMessage(pattern='/support'))
async def support(event):
    await event.reply("👨‍💻 **SUPPORT**\nContact me on WhatsApp for help.", 
                     buttons=[[Button.url("💬 WhatsApp", "https://wa.me/message/S3CQYVGPGOZ4H1")]])

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT expiry_time FROM approved_users WHERE user_id=%s AND expiry_time > NOW()", (event.sender_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    msg = f"✅ **VIP ACTIVE**\nExpires: `{row[0]}`" if row else "📉 **FREE TIER**\nNo active VIP found."
    await event.reply(msg)

# --- CALLBACKS (Approve, Reject, Ban) ---
@client.on(events.CallbackQuery())
async def callbacks(event):
    data = event.data.decode()
    user = await event.get_sender()
    
    if data == "claim_pay":
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}")],
                [Button.inline("❌ Reject", data=f"rej_{user.id}")],
                [Button.inline("🚫 BAN", data=f"ban_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"💰 **PAYMENT CLAIM**\nUser: {user.first_name}\nID: `{user.id}`", buttons=btns)
        await event.answer("📩 Verification sent to Mr. White.", alert=True)

    elif data.startswith("rej_"):
        uid = int(data.split("_")[1])
        await client.send_message(uid, "❌ **CLAIM REJECTED**\nPayment not found. Please pay via Selar first.")
        await event.edit(f"❌ User {uid} Rejected.")

    elif data.startswith("app_"):
        uid = int(data.split("_")[1])
        database.approve_user_24h(uid)
        await client.send_message(uid, "✅ **ACCESS GRANTED.**\nUse /ticket to see the uncovered ticket!")
        await event.edit(f"✅ User {uid} Approved.")

# --- THE MESSAGE HANDLER (Handles AI & Forwards) ---
@client.on(events.NewMessage())
async def handle_messages(event):
    # If it's a command or from Admin, STOP here
    if event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    
    user = await event.get_sender()
    # Forward to you
    await client.send_message(config.ADMIN_ID, f"📩 **Msg from {user.first_name}** (`{user.id}`):\n{event.raw_text}", 
                              buttons=[[Button.inline("💬 Reply", data=f"reply_{user.id}")]])

    # AI Reply
    reply = await generate_ai_reply(user.id, event.raw_text)
    if reply:
        await asyncio.sleep(1)
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]])

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Full Vision Active")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
