import os
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import database  # Your local database.py
import config    # Your local config.py

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is running"}

# -----------------------
# Telegram Bot Client
# -----------------------
bot = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# -----------------------
# /start Command
# -----------------------
@bot.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳 Buy Ticket ¢150", url=config.SELAR_PAYMENT_LINK)]]
    )

    caption = (
        "🎉 WELCOME to Victory Odds Premium Tips Bot!\n\n"
        "EVERY DAY, you can access a DAILY PREMIUM TICKET with exclusive tips.\n\n"
        "💡 HOW TO USE:\n"
        "1️⃣ Click the button below to purchase today’s ticket\n"
        "2️⃣ Complete the payment securely via Selar\n"
        "3️⃣ Receive your ticket instantly!\n\n"
        "📌 NOTE: Tickets are available once per day per user\n"
        "⚡ Stay updated for daily premium tips and predictions!"
    )

    await message.reply_photo(
        photo=config.TICKET_URL,
        caption=caption,
        reply_markup=keyboard
    )

# -----------------------
# Selar Webhook Endpoint
# -----------------------
@app.post("/selar-webhook")
async def selar_webhook(request: Request):
    data = await request.json()

    # Extract relevant fields
    user_id = int(data.get("user_id", 0))  # You must pass Telegram ID in Selar metadata
    product_id = data.get("product_id")
    status = data.get("status")  # "success", "failed", etc.

    # Verify the product is correct
    if status == "success" and product_id == config.SELAR_PRODUCT_ID:
        # Mark user as paid for the day
        database.mark_paid(user_id)
        database.add_payment(user_id, data.get("transaction_id"), data.get("amount"), "success")

        # Send ticket photo
        await bot.send_photo(user_id, config.TICKET_URL)

    elif status == "failed" and user_id:
        await bot.send_message(user_id, "❌ Your payment failed. Please try again.")

    return {"status": "ok"}

# -----------------------
# Admin Commands
# -----------------------
@bot.on_message(filters.command("broadcast") & filters.user(config.ADMIN_ID))
async def broadcast(client, message):
    if len(message.text.split(" ", 1)) < 2:
        await message.reply_text("Usage: /broadcast Your message here")
        return
    text = message.text.split(" ", 1)[1]

    all_users = database.get_all_users()
    for user_id in all_users:
        try:
            await bot.send_message(user_id, text)
        except:
            continue
    await message.reply_text("✅ Broadcast sent.")

@bot.on_message(filters.command("stats") & filters.user(config.ADMIN_ID))
async def stats(client, message):
    count = database.count_today_purchases()
    await message.reply_text(f"📊 Users who purchased today: {count}")

# -----------------------
# Startup & Shutdown
# -----------------------
@app.on_event("startup")
async def startup():
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    await bot.stop()