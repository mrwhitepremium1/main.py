import logging, asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, UserIsBlockedError, PeerIdInvalidError
import config, database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v70', config.API_ID, config.API_HASH)
pending_replies = {}

# --- ADMIN COMMANDS ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID, incoming=True))
async def admin_handler(event):
    global pending_replies
    text = event.raw_text.strip()
    
    if event.sender_id in pending_replies and not text.startswith('/'):
        uid = pending_replies.pop(event.sender_id)
        try:
            await client.send_message(uid, f"👨‍💼 **Mr. White Support:**\n\n{text}")
            await event.reply(f"✅ **Sent to `{uid}`**")
        except: await event.reply("❌ **Failed.** User blocked bot.")
        return

    if text.startswith('/find '):
        uid = int(text.split(' ')[1])
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT username, last_seen, approved_until FROM subscribers WHERE user_id = %s", (uid,))
        res = cur.fetchone(); cur.close(); conn.close()
        if res:
            status = "✅ Active" if res[2] and datetime.now() < res[2] else "❌ Inactive"
            await event.reply(f"🔍 **User Found:**\n🆔 ID: `{uid}`\n👤 @{res[0]}\n🕒 Seen: {res[1]}\n📊 {status}")
        else: await event.reply("❌ User not found.")

    elif text.startswith('/broadcast'):
        msg = text.replace('/broadcast', '').strip()
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall(); cur.close(); conn.close()
        await event.reply(f"📣 **Broadcasting to {len(users)} users...**")
        for u in users:
            try:
                if event.media: await client.send_file(u[0], event.media, caption=msg)
                else: await client.send_message(u[0], msg)
                await asyncio.sleep(0.5)
            except: continue
        await event.reply("✅ **Broadcast Done.**")

# --- USER COMMANDS & WELCOME ---
@client.on(events.NewMessage(pattern='/start', incoming=True))
async def start(event):
    if event.sender_id == config.ADMIN_ID: return
    user = await event.get_sender()
    uid = user.id
    
    database.init_db() # Self-healing DB check
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET last_seen = %s", (uid, user.username, datetime.now(), datetime.now()))
    conn.commit(); cur.close(); conn.close()

    welcome = (f"Hello 👋 {user.first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
               "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
               "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** 100% Guaranteed")
    
    btns = [[Button.url("💰 Crypto (Automatic)", "https://pay.oxapay.com/10368962")],
            [Button.url("🌍 International / Mobile Money", config.SELAR_PAYMENT_LINK)],
            [Button.inline("✅ I Have Paid", data="claim_pay")]]
    
    await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)
    
    adm_btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🚫 Block", data=f"preblk_{uid}")]]
    await client.send_message(config.ADMIN_ID, f"👤 **New Visitor!**\nID: `{uid}`", buttons=adm_btns)

@client.on(events.NewMessage(pattern='/support'))
async def support(event): await event.reply("💬 **Support Connected.** Send your message now.")

@client.on(events.NewMessage(incoming=True))
async def forwarder(event):
    if event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/'): return
    user = await event.get_sender()
    btns = [[Button.inline("💬 Reply", data=f"qr_{user.id}"), Button.inline("🚫 Block", data=f"preblk_{user.id}")]]
    await client.send_message(config.ADMIN_ID, f"📩 **MSG FROM `{user.id}`**", buttons=btns)
    await client.forward_messages(config.ADMIN_ID, event.message)

# --- CALLBACK HANDLER ---
@client.on(events.CallbackQuery())
async def callbacks(event):
    global pending_replies
    data = event.data.decode()
    if data == "claim_pay":
        user = await event.get_sender()
        await event.answer("✅ Sent to Admin.", alert=True)
        btns = [[Button.inline("✅ Approve", data=f"app_{user.id}")], [Button.inline("❌ Reject", data=f"rej_{user.id}")]]
        await client.send_message(config.ADMIN_ID, f"🚨 **PAYMENT CLAIM**\nID: `{user.id}`", buttons=btns)
    elif data.startswith('app_'):
        uid = int(data.split('_')[1])
        database.approve_user_24h(uid)
        await event.edit(f"✅ Approved {uid}"); await client.send_message(uid, "✅ **Payment Verified!** Access active for 24h.")
    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        await event.edit(f"❌ Rejected {uid}"); await client.send_message(uid, "❌ **Payment Rejected.** Contact support.")
    elif data.startswith('qr_'):
        uid = int(data.split('_')[1]); pending_replies[config.ADMIN_ID] = uid; await event.answer("✍️ Type reply...", alert=True)
    elif data.startswith('preblk_'):
        uid = int(data.split('_')[1]); await event.edit(f"Block `{uid}`?", buttons=[[Button.inline("✅ Yes", data=f"cblk_{uid}"), Button.inline("❌ No", data="can")]])
    elif data.startswith('cblk_'):
        uid = int(data.split('_')[1]); conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,)); conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 Blocked `{uid}`.")
    elif data == "can": await event.edit("Cancelled.")

async def main():
    database.init_db()
    await client.start(bot_token=config.BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
