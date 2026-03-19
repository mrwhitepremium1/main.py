import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)

# --- AI CORE ---
async def generate_ai_reply(user_id, message, context="general"):
    # Always check sleep mode first
    if database.get_sleep_mode(): return None
    
    history = database.get_user_memory(user_id) or ""
    
    # Custom prompts based on what the user clicked
    if context == "support":
        prompt = f"User needs help/support. Explain that you are Mr. White and you provide verified fixed tickets. Tell them to buy via Selar or ask you a question. History: {history}\nUser: {message}"
    else:
        prompt = f"You are Mr. White, a wealthy betting expert from Ghana. Use short, punchy sentences. Encourage them to buy the VIP ticket on Selar. History: {history}\nUser: {message}"

    try:
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=150
        )
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1000:])
        return reply
    except Exception as e:
        print(f"AI Error: {e}")
        return "The markets are heating up. Get your VIP access now to join the winners. 📈"

# --- FIXED START COMMAND ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # This now works for EVERYONE
    welcome_text = (
        "Hello 👋 **Mr White!**\n\n"
        "**Welcome to Mr. White | Official Bot**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "💎 **PREMIUM INFO ARRIVED**\n"
        "⭐ **CONFIRMED TICKET** 🎫\n\n"
        "☑️ **Fixed Tips:** Correct Score\n"
        "✔️ **Verification:** 100% Guaranteed\n\n"
        "To access today's confirmed selections, please check the price via the link below and click 'I Have Paid'."
    )
    btns = [
        [Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)],
        [Button.inline("✅ I Have Paid", data="claim_pay")]
    ]
    await event.reply(welcome_text, file=config.COVERED_TICKET_URL, buttons=btns)

# --- SUPPORT COMMAND (AI DRIVEN) ---
@client.on(events.NewMessage(pattern='/support'))
async def support_ai(event):
    # Instead of just a link, the AI explains support
    reply = await generate_ai_reply(event.sender_id, "I need support/help", context="support")
    await event.reply(f"🤖 {reply}", buttons=[[Button.url("💬 Chat on WhatsApp", "https://wa.me/message/S3CQYVGPGOZ4H1")]])

# --- MAIN MESSAGE HANDLER ---
@client.on(events.NewMessage())
async def handle_messages(event):
    # 1. Ignore if it's a command (those are handled above)
    if event.raw_text.startswith('/'): return
    
    # 2. Ignore if it's the ADMIN account
    if event.sender_id == config.ADMIN_ID: return
    
    # 3. Handle Regular Users
    user = await event.get_sender()
    
    # Forward message to you so you can see it
    await client.send_message(config.ADMIN_ID, f"📩 **Msg from {user.first_name}** (`{user.id}`):\n{event.raw_text}", 
                              buttons=[[Button.inline("💬 Reply", data=f"reply_{user.id}")]])

    # AI Reply
    reply = await generate_ai_reply(user.id, event.raw_text)
    if reply:
        await asyncio.sleep(1) # Make it look like it's typing
        await event.reply(f"🤖 {reply}", buttons=[
            [Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]
        ])
