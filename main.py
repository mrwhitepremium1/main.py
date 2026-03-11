import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

# store users
users = set()

# daily ticket
daily_ticket = None

bot = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# START COMMAND
@bot.on_message(filters.command("start"))
async def start(client, message):

    users.add(message.from_user.id)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Buy Ticket GHS 150", url=config.SELAR_PAYMENT_LINK)],
            [InlineKeyboardButton("📩 I Have Paid", callback_data="paid")]
        ]
    )

    caption = (
        "🔥 Welcome to the Premium Betting Bot!\n\n"
        "Daily VIP ticket available.\n\n"
        "Click BUY TICKET to purchase today's ticket."
    )

    await message.reply_photo(
        photo=config.WELCOME_IMAGE,
        caption=caption,
        reply_markup=keyboard
    )


# USER CLAIM PAYMENT
@bot.on_callback_query(filters.regex("paid"))
async def paid(client, callback_query):

    await callback_query.message.reply_text(
        "✅ Payment received.\n\nAdmin will verify and send your ticket shortly."
    )


# ADMIN UPLOAD DAILY TICKET
@bot.on_message(filters.photo & filters.user(config.ADMIN_ID))
async def upload_ticket(client, message):

    global daily_ticket

    daily_ticket = message.photo.file_id

    await message.reply_text("✅ Daily ticket updated successfully!")


# ADMIN SEND TICKET TO USER
@bot.on_message(filters.command("send") & filters.user(config.ADMIN_ID))
async def send_ticket(client, message):

    if not daily_ticket:
        await message.reply_text("❌ No ticket uploaded today.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: /send USER_ID")
        return

    user_id = int(message.command[1])

    await bot.send_photo(
        user_id,
        daily_ticket,
        caption="🎟 Here is today's premium ticket!"
    )

    await message.reply_text("✅ Ticket sent.")


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

    await message.reply_text(f"Broadcast sent to {sent} users")


# STATS
@bot.on_message(filters.command("stats") & filters.user(config.ADMIN_ID))
async def stats(client, message):

    await message.reply_text(f"Total users: {len(users)}")


# RUN BOT
async def main():
    await bot.start()
    print("Bot is running...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())