import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from openai import OpenAI
import config
import database

ai_client = OpenAI(api_key=config.OPENAI_API_KEY)
client = TelegramClient('mr_white_session', config.API_ID, config.API_HASH)

# --- AI CORE (The Brain) ---
async def generate_ai_reply(user_id, message, context="general"):
    if database.get_sleep_mode(): return None
    
    history = database.get_user_memory(user_id) or ""
    # Giving the AI specific instructions for Support vs General Chat
    system_prompt = (
        "You are Mr. White, a wealthy betting expert from Ghana. "
        "If the user asks for support, explain that you provide 100% verified tickets. "
        "Always be short, professional, and encourage them to buy the VIP ticket on Selar."
    )
    
    try:
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"History: {history}\nUser Message: {message}"}
            ],
            max_tokens=150
        )
        reply = res.choices[0].message.content
        database.save_user_memory(user_id, (history + f"\nUser:{message}\nAI:{reply}")[-1000:])
        return reply
    except:
        return "The markets are moving fast. Secure your VIP spot to see the winning green. 📈"

# --- VIP TICKET (Uncovered Image) ---
@client.on(events.NewMessage(pattern='/ticket'))
async def ticket_cmd(event):
    # Check if user is in approved_users table and not expired
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT expiry_time FROM approved_users WHERE user_id=%s AND expiry_time > NOW()", (event.sender_id,))
    is_vip = cur.fetchone(); cur.close(); conn.close()
    
    if is_vip:
        await event.reply("💎 **YOUR UNCOVERED TICKET**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nHere is your verified info. Stake wisely! 🎫", file=config.TICKET_URL)
    else:
        await event.reply("❌ **ACCESS DENIED**\nYou need an active VIP subscription. Buy below:", 
                         buttons=[[Button.url("💳 Buy VIP Ticket", config.SELAR_PAYMENT_LINK)]])

# --- ADMIN: BROADCAST & SLEEP ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_commands(event):
    cmd = event.raw_text.lower()
    
    if cmd.startswith('/broadcast'):
        parts = event.raw_text.split(' ', 1)
        msg_text = parts[1] if len(parts) > 1 else "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫"
        
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall()
        cur.close(); conn.close()
        
        for u in users:
            try:
                msg = await client.send_message(u[0], msg_text, file=config.COVERED_TICKET_URL, 
                                               buttons=[[Button.url("💳 Buy Ticket", config.SELAR_PAYMENT_LINK)], 
                                                        [Button.inline("✅ I Have Paid", data="claim_pay")]])
                await client.pin_message(u[0], msg.id)
                await asyncio.sleep(0.3)
            except: continue
        await event.reply(f"✅ Broadcast sent to {len(users)} users.")

    elif cmd.startswith('/sleep'):
        mode = "on" in cmd
        database.set_sleep_mode(mode)
        await event.reply(f"😴 **Sleep Mode:** {'ON (AI Paused)' if mode else 'OFF (AI Active)'}")

# --- USER: SUPPORT & START ---
@client.on(events.NewMessage())
async def handle_all(event):
    if not event.is_private or event.sender_id == config.ADMIN_ID: return
    
    # Priority 1: Start Command
    if event.raw_text.startswith('/start'):
        welcome = "Hello 👋 **Mr White!**\n\n**Welcome to Mr. White | Official Bot**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nTo access today's confirmed selections, please check the price below."
        btns = [[Button.url("💳 Check Price & Buy Ticket", config.SELAR_PAYMENT_LINK)], [Button.inline("✅ I Have Paid", data="claim_pay")]]
        await event.reply(welcome, file=config.COVERED_TICKET_URL, buttons=btns)
        return

    # Priority 2: Support (AI Driven)
    if event.raw_text.startswith('/support'):
        reply = await generate_ai_reply(event.sender_id, "Explain your support and how to get the ticket.")
        await event.reply(f"🤖 {reply}", buttons=[[Button.url("💬 WhatsApp Admin", "https://wa.me/message/S3CQYVGPGOZ4H1")]])
        return

    # Priority 3: General Chat (AI)
    reply = await generate_ai_reply(event.sender_id, event.raw_text)
    if reply:
        await event.reply(f"🤖 {reply}")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    print("🚀 Mr. White Final Vision Online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
