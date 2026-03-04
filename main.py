import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

# In-memory database for demonstration (replace with real DB if needed)
users_db = set()

bot = Client(
    "premium_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# /start command
@bot.on_message(filters.command("start"))
async def start(client, message):
    users_db.add(message.from_user.id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💳 Buy Ticket ¢150",
                    url=config.PAYSTACK_PAYMENT_LINK.format(user_id=message.from_user.id)
                )
            ]
        ]
    )

    caption = (
        "🔥 Welcome!\n\n"
        "Daily Premium Ticket is available.\n"
        "Click below to pay and receive your ticket."
    )

    await message.reply_photo(
        photo=config.TICKET_URL,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# /broadcast command (admin only)
@bot.on_message(filters.command("broadcast") & filters.user(config.ADMIN_ID))
async def broadcast(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /broadcast Your message here")
        return

    text = message.text.split(maxsplit=1)[1]
    count = 0
    for user_id in users_db:
        try:
            await bot.send_message(user_id, text)
            count += 1
        except:
            continue
    await message.reply_text(f"Broadcast sent to {count} users.")

# /stats command (admin only)
@bot.on_message(filters.command("stats") & filters.user(config.ADMIN_ID))
async def stats(client, message):
    await message.reply_text(f"Total users: {len(users_db)}")

# Run the bot
async def main():
    await bot.start()
    print("Bot is running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())