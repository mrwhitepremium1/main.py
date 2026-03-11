import asyncio
from fastapi import FastAPI, Request
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

app = FastAPI()

bot = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# -----------------------
# START COMMAND
# -----------------------

@bot.on_message(filters.command("start"))
async def start(client, message):

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Buy Ticket ¢150", url=config.SELAR_PAYMENT_LINK)]
        ]
    )

    caption = (
        "🔥 **Welcome to Victory Odds Premium Bot!**\n\n"
        "Today's premium ticket is available.\n\n"
        "Click the button below to purchase today's ticket."
    )

    await message.reply_photo(
        photo=config.TICKET_IMAGE,
        caption=caption,
        reply_markup=keyboard
    )

# -----------------------
# SELAR WEBHOOK
# -----------------------

@app.post("/selar-webhook")
async def selar_webhook(request: Request):

    data = await request.json()

    # Example Selar payload
    email = data.get("customer_email")
    telegram_id = data.get("custom_fields", {}).get("telegram_id")

    if telegram_id:
        try:
            await bot.send_photo(
                chat_id=int(telegram_id),
                photo=config.TICKET_IMAGE,
                caption="✅ Payment received!\n\nHere is today's premium ticket 🎟"
            )
        except:
            pass

    return {"status": "success"}

# -----------------------
# ADMIN BROADCAST
# -----------------------

users = set()

@bot.on_message(filters.command("broadcast") & filters.user(config.ADMIN_ID))
async def broadcast(client, message):

    text = message.text.split(None, 1)[1]

    for user in users:
        try:
            await bot.send_message(user, text)
        except:
            pass

    await message.reply_text("Broadcast sent.")

# -----------------------
# BOT STARTUP
# -----------------------

@app.on_event("startup")
async def startup():
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    await bot.stop()