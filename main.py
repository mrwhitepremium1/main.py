import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

users = set()
daily_ticket = None

bot = Client(
    "premium_ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# START
@bot.on_message(filters.command("start"))
async def start(client, message):

    users.add(message.from_user.id)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Buy Ticket GHS 150", url=config.SELAR_PAYMENT_LINK)],
            [InlineKeyboardButton("✅ I Have Paid", callback_data="paid")]
        ]
    )

    text = (
        "🔥 *Welcome to Premium Betting Bot*\n\n"
        "Get today's VIP betting ticket.\n\n"
        "1️⃣ Click BUY TICKET\n"
        "2️⃣ Complete payment\n"
        "3️⃣ Click I HAVE PAID\n\n"
        "Admin will verify and send ticket."
    )

    await message.reply_photo(
        photo=config.WELCOME_IMAGE,
        caption=text,
        reply_markup=keyboard
    )

# USER CLAIM PAYMENT
@bot.on_callback_query(filters.regex("paid"))
async def claim_payment(client, query):

    user = query.from_user

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}")
            ]
        ]
    )

    await bot.send_message(
        config.ADMIN_ID,
        f"💰 Payment Claim\n\nUser: {user.mention}\nID: {user.id}",
        reply_markup=keyboard
    )

    await query.message.reply_text(
        "⏳ Payment request sent to admin.\n\nPlease wait for approval."
    )

# ADMIN APPROVE PAYMENT
@bot.on_callback_query(filters.regex("approve_"))
async def approve_payment(client, query):

    global daily_ticket

    user_id = int(query.data.split("_")[1])

    if not daily_ticket:
        await query.message.reply_text("❌ No ticket uploaded today.")
        return

    await bot.send_photo(
        user_id,
        daily_ticket,
        caption="🎟 Here is today's premium ticket!"
    )

    await query.message.edit_text("✅ Ticket sent to user.")

# ADMIN UPLOAD DAILY TICKET
@bot.on_message(filters.photo & filters.user(config.ADMIN_ID))
async def upload_ticket(client, message):

    global daily_ticket

    daily_ticket = message.photo.file_id

    await message.reply_text("✅ Daily ticket updated!")

# BROADCAST
@bot.on_message(filters.command("broadcast") & filters.user(config.ADMIN_ID))
async def broadcast(client, message):

    text = message.text.split(None, 1)[1]

    sent = 0

    for user in users:
        try:
            await bot.send_message(user, text)
            sent += 1
        except:
            pass

    await message.reply_text(f"Broadcast sent to {sent} users.")

# STATS
@bot.on_message(filters.command("stats") & filters.user(config.ADMIN_ID))
async def stats(client, message):

    await message.reply_text(f"Total users: {len(users)}")

# RUN
async def main():
    await bot.start()
    print("Bot Running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())