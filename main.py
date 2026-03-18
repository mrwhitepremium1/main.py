import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
import config
import database

# --- SETTINGS ---
sleep_mode_active = False 
OFFLINE_MSG = "🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed as soon as he is back online. Thank you for your patience! 🎯"

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_master_v38', config.API_ID, config.API_HASH)

# --- 1. ADMIN COMMANDS (SMART REPLY & MEDIA) ---

# FEATURE: Reply to a forwarded message OR use /reply ID
@client.on(events.NewMessage(incoming=True))
async def admin_smart_reply(event):
    if event.sender_id != config.ADMIN_ID or not event.is_reply:
        return

    # 1. Check if replying to a forwarded message from the bot
    replied_msg = await event.get_reply_message()
    
    # Extract ID from our own bot's support/visitor header format
    target_id = None
    if replied_msg.text:
        import re
        match = re.search(r'🆔: `(\d+)`|ID: `(\d+)`', replied_msg.text)
        if match:
            target_id = int(match.group(1) or match.group(2))

    # 2. Handle /reply command pattern
    if event.raw_text.startswith('/reply'):
        parts = event.raw_text.split(maxsplit=2)
        if len(parts) >= 2:
            target_id = int(parts[1])
            msg_content = parts[2] if len(parts) > 2 else ""
        else: return
    else:
        msg_content = event.raw_text

    if target_id:
        try:
            header = "👨‍💼 **Mr. White Support:**\n\n"
            if event.media:
                await client.send_file(target_id, event.media, caption=f"{header}{msg_content}")
            else:
                await client.send_message(target_id, f"{header}{msg_content}")
            await event.reply(f"✅ **Sent to `{target_id}`**")
        except Exception as e:
            await event.reply(f"❌ **Error:** {str(e)}")

@client.on(events.NewMessage(pattern=r'/block (\d+)'))
async def block_user(event):
    if event.sender_id != config.ADMIN_ID: return
    uid = int(event.pattern_match.group(1))
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    await event.reply(f"🚫 **User `{uid}` blocked.**")

@client.on(events.NewMessage(pattern='/users'))
async def list_users(event):
    if event.sender_id != config.ADMIN_ID: return
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
    cur.close(); conn.close()
    await event.reply(f"📊 **Total Subscribers: {total}**") # Currently at 59

# --- 2. USER COMMANDS ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = await event.get_sender()
    first_name = user.first_name if user.first_name else "No Name"
    # Capture name/ID for alert
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor Alert!**\nName: {first_name}\nID: `{user.id}`")
    
    buttons = [[Button.inline("💳 Check Price & Buy Ticket", data="pay_options")],
               [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    welcome_text = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n☑ **Fixed Tips:** Correct Score\n"
                    f"✔ **Verification:** 100% Guaranteed")
    await client.send_file(event.chat_id, config.COVERED_TICKET_URL, caption=welcome_text, buttons=buttons)

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    msg = "📊 Status: Active 🤝" if database.is_user_approved(event.sender_id) else "📊 Status: Inactive ❌"
    await event.reply(msg)

# --- 3. UPDATED 40 USD PAYMENT & CALLBACKS ---

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode()
    if data == "pay_options":
        pay_btns = [[Button.url("🌍 Africa (MoMo/Card)", config.SELAR_PAYMENT_LINK)],
                    [Button.inline("💰 Crypto (USDT)", data="pay_crypto")],
                    [Button.inline("⬅️ Back", data="back_start")]]
        await event.edit("🎯 **Select your payment method:**", buttons=pay_btns)

    elif data == "pay_crypto":
        # 40 USD OxaPay link
        msg = "💎 **Cryptocurrency Payment**\n\nPrice: **40 USD**\nClick below to pay with Crypto."
        await event.edit(msg, buttons=[[Button.url("🔗 Pay 40 USD", "https://pay.oxapay.com/10368962")],
                                       [Button.inline("⬅️ Back", data="pay_options")]])

    elif data == "claim_pay":
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{event.sender_id}"), Button.inline("❌ Reject", data=f"rej_{event.sender_id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **New Claim!**\nID: `{event.sender_id}`", buttons=btns)

# --- 4. FORWARDING ---
@client.on(events.NewMessage())
async def handle_incoming(event):
    if not event.is_private or event.raw_text.startswith('/') or event.sender_id == config.ADMIN_ID: return
    if sleep_mode_active: await event.reply(OFFLINE_MSG)
    user = await event.get_sender()
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT MESSAGE**\n👤: {user.first_name}\n🆔: `{user.id}`")
    await client.forward_messages(config.ADMIN_ID, event.message)

async def main():
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
