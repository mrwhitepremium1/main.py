import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
import config, database

logging.basicConfig(level=logging.INFO)
client = TelegramClient('mr_white_v85', config.API_ID, config.API_HASH)
pending_replies = {}
sleep_mode_active = False

# --- 1. CORE COMMANDS ---
@client.on(events.NewMessage(pattern=r'^/(start|status|support)'))
async def core_commands(event):
    global sleep_mode_active
    cmd = event.pattern_match.group(1).lower()
    uid, user = event.sender_id, await event.get_sender()
    first_name = user.first_name or "User"
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if cmd == 'start':
        database.init_db()
        conn = database.get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO subscribers (user_id, username, last_seen) VALUES (%s, %s, %s) "
                    "ON CONFLICT (user_id) DO UPDATE SET last_seen = %s, username = %s", 
                    (uid, user.username, datetime.now(), datetime.now(), user.username))
        conn.commit(); cur.close(); conn.close()

        # Visitor Alert with View Profile Photo Button
        if uid != config.ADMIN_ID:
            adm_btns = [
                [Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🖼 View DP", data=f"pfp_{uid}")],
                [Button.inline("🚫 Block", data=f"blk_{uid}")]
            ]
            status_tag = " (🌙 Offline)" if sleep_mode_active else ""
            alert = (f"👤 **New Visitor Alert!**{status_tag}\n━━━━━━━━━━━━━━━━━━━━\n"
                     f"**Name:** {first_name}\n**ID:** `{uid}`\n**User:** @{user.username}\n"
                     f"🕒 **Joined At:** `{now_time}`")
            await client.send_message(config.ADMIN_ID, alert, buttons=adm_btns)

        if sleep_mode_active and uid != config.ADMIN_ID:
            return await event.reply("🌙 **Mr. White is currently offline.**\nYour request has been logged. Support will attend to you shortly. 🎯")

        welcome = (f"Hello 👋 {first_name}!\n\n**Welcome to Mr. White | Official Bot**\n━━━━━━━━━━━━━━━━━━━━\n"
                   "💎 **PREMIUM INFO ARRIVED**\n⭐ **CONFIRMED TICKET** 🎫\n\n"
                   "☑ **Fixed Tips:** Correct Score\n✔ **Verification:** Confirmed Selections")
        
        crypto_url = f"https://pay.oxapay.com/10368962?orderId={uid}"
        btns = [[Button.url("💰 Crypto (Automatic)", crypto_url)],
                [Button.inline("📜 T&C's", data="view_tcs")]]
        await client.send_file(uid, config.COVERED_TICKET_URL, caption=welcome, buttons=btns)

    elif cmd == 'status':
        is_active = database.is_user_approved(uid)
        await event.reply("📊 Status: **Active** ✅" if is_active else "📊 Status: **Inactive** ❌")

    elif cmd == 'support':
        await event.reply("💬 **Connected to Support.**\nExplain your issue clearly; Mr. White is listening. 🎯")

# --- 2. ADMIN SUITE ---
@client.on(events.NewMessage(from_users=config.ADMIN_ID))
async def admin_suite(event):
    global pending_replies, sleep_mode_active
    text = event.raw_text.strip()
    
    if text.startswith('/'):
        cmd = text.lower()
        if cmd == '/users':
            conn = database.get_connection(); cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM subscribers"); total = cur.fetchone()[0]
            cur.close(); conn.close(); await event.reply(f"📊 **Total Subscribers:** {total}")
            
        elif cmd.startswith('/find'):
            try:
                search_id = int(text.split(' ')[1])
                user_data = database.get_user_info(search_id)
                if user_data:
                    uid, uname, seen, approved = user_data
                    active = "✅ Active" if database.is_user_approved(uid) else "❌ Inactive"
                    await event.reply(f"🔍 **User Found:**\n🆔 **ID:** `{uid}`\n👤 @{uname}\n🕒 **Last Seen:** {seen}\n📊 {active}")
                else: await event.reply("❌ User not found.")
            except: await event.reply("⚠️ Usage: `/find [ID]`")

        elif cmd.startswith('/sleep'):
            sleep_mode_active = ("on" in cmd)
            await event.reply(f"**Sleep Mode {'Enabled 🌙' if sleep_mode_active else 'Disabled ☀️'}**")

        elif cmd.startswith('/broadcast'):
            msg_content = text[10:].strip()
            reply_msg = await event.get_reply_message() if event.is_reply else None
            media = event.media if event.media else (reply_msg.media if reply_msg else None)
            conn = database.get_connection(); cur = conn.cursor(); cur.execute("SELECT user_id FROM subscribers"); users = cur.fetchall(); cur.close(); conn.close()
            
            status_msg = await event.reply(f"🚀 **Broadcasting...**")
            success, blocked = 0, 0
            for u in users:
                try:
                    if media: await client.send_file(u[0], media, caption=msg_content)
                    else: await client.send_message(u[0], msg_content)
                    success += 1
                    await asyncio.sleep(0.3)
                except: blocked += 1
            await status_msg.edit(f"✅ **Broadcast Done**\n━━━━━━━━━━━━━━━━━━━━\n📤 **Sent:** {success}\n🚫 **Blocked:** {blocked}")
        return

    if event.sender_id in pending_replies:
        uid = pending_replies.pop(event.sender_id)
        prefix = "👨‍💼 **Mr. White Support:**\n\n"
        if event.media: await client.send_file(uid, event.media, caption=f"{prefix}{text}" if text else prefix)
        else: await client.send_message(uid, f"{prefix}{text}")
        await event.reply(f"✅ **Replied to `{uid}`**")

# --- 3. SUPPORT FORWARDER ---
@client.on(events.NewMessage(incoming=True))
async def support_forwarder(event):
    if event.sender_id == config.ADMIN_ID or event.raw_text.startswith('/') or not event.is_private: return
    
    uid = event.sender_id
    user = await event.get_sender()
    now_time = datetime.now().strftime("%H:%M:%S")

    if sleep_mode_active:
        await event.reply("🌙 **Mr. White is currently offline.**\nYour message has been received and will be reviewed once back online. 🎯")

    btns = [[Button.inline("💬 Reply", data=f"qr_{uid}"), Button.inline("🖼 View DP", data=f"pfp_{uid}")]]
    await client.send_message(config.ADMIN_ID, f"📩 **SUPPORT FROM `{uid}`**\n🕒 **Time:** `{now_time}`", buttons=btns)
    await client.forward_messages(config.ADMIN_ID, event.message)

# --- 4. CALLBACKS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    global pending_replies
    data = event.data.decode()

    if data.startswith('pfp_'):
        uid = int(data.split('_')[1])
        try:
            photos = await client.get_profile_photos(uid, limit=1)
            if photos:
                await client.send_file(config.ADMIN_ID, photos[0], caption=f"🖼 **Profile Picture for ID:** `{uid}`")
            else:
                await event.answer("❌ User has no profile photo.", alert=True)
        except Exception as e:
            await event.answer(f"❌ Error: {str(e)}", alert=True)

    elif data == "view_tcs":
        tcs = ("📜 **Terms & Conditions**\n━━━━━━━━━━━━━━━━━━━━\n"
               "1. All sales are final. No refunds.\n"
               "2. Tips are for info only. Stake responsibly.\n"
               "3. Access is strictly limited to 24 hours.\n"
               "4. Multiple accounts = permanent ban.")
        await event.respond(tcs)

    elif data.startswith('app_'):
        uid = int(data.split('_')[1]); database.approve_user_24h(uid)
        msg = ("✅ **PAYMENT VERIFIED**\n━━━━━━━━━━━━━━━━━━━━\n🎫 **TICKET ISSUED**\n\nActive for **24 Hours**.")
        await client.send_file(uid, config.TICKET_URL, caption=msg)
        await event.edit(f"✅ **Approved `{uid}`**")

    elif data.startswith('rej_'):
        uid = int(data.split('_')[1])
        rej = ("❌ **Payment Rejected**\n\nCould not verify payment. Contact support.")
        await client.send_message(uid, rej); await event.edit(f"❌ **Rejected `{uid}`**")

    elif data.startswith('blk_'):
        uid = int(data.split('_')[1]); conn = database.get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id = %s", (uid,)); conn.commit(); cur.close(); conn.close()
        await event.edit(f"🛑 **User `{uid}` Deleted.**")

    elif data.startswith('qr_'):
        pending_replies[config.ADMIN_ID] = int(data.split('_')[1]); await event.answer("✍️ Send reply...", alert=True)

async def main():
    database.init_db(); await client.start(bot_token=config.BOT_TOKEN); await client.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
