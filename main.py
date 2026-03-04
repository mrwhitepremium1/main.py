import os
import json
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import database  # Your database.py file
import config    # Your config.py file

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
    # Inline buttons for Paystack & NOWPayments
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Pay with Paystack ¢150", url=config.PAYSTACK_PAYMENT_LINK.format(user_id=message.from_user.id))],
            [InlineKeyboardButton("💰 Pay with Crypto", url=config.NOWPAYMENTS_LINK + f"&metadata[user_id]={message.from_user.id}")]
        ]
    )

    caption = (
        "🎉 *WELCOME to Victory Odds Premium Tips Bot!*\n\n"
        "🔥 *Daily Premium Ticket Available!*\n\n"
        "📌 *How it works:*\n"
        "1️⃣ Click the button below to purchase today’s ticket\n"
        "2️⃣ Complete payment securely via Paystack or NOWPayments\n"
        "3️⃣ Receive your ticket instantly\n\n"
        "⚡ *Note:*\n"
        "Tickets are limited to one per day per user\n"
        "Stay tuned for exclusive daily premium tips and predictions!"
    )

    await message.reply_photo(
        photo=config.TICKET_URL,
        caption=caption,
        parse_mode="md",  # ✅ Correct parse mode
        reply_markup=keyboard
    )

# -----------------------
# Paystack Webhook
# -----------------------
@app.post("/paystack-webhook")
async def paystack_webhook(request: Request):
    data = await request.json()
    user_id = int(data["metadata"]["user_id"])
    status = data["event"]

    if status == "charge.success":
        database.mark_paid(user_id)
        database.add_payment(user_id, data["data"]["reference"], data["data"]["amount"], "success")
        await bot.send_photo(user_id, config.TICKET_URL)
    elif status == "charge.failed":
        await bot.send_message(user_id, "❌ Your payment failed. Please try again.")

    return {"status": "ok"}

# -----------------------
# NOWPayments Webhook
# -----------------------
@app.post("/nowpayments-webhook")
async def nowpayments_webhook(request: Request):
    data = await request.json()
    user_id = int(data["order_id"].split("-")[1])  # Extract Telegram user_id from order_id
    status = data.get("payment_status")

    if status == "finished":
        database.mark_paid(user_id)
        database.add_payment(user_id, data.get("payment_id"), data.get("price_amount"), "success")
        await bot.send_photo(user_id, config.TICKET_URL)
    elif status == "failed":
        await bot.send_message(user_id, "❌ Your crypto payment failed. Please try again.")

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