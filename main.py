import os
import json
import hmac
import hashlib
import requests
from datetime import date
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import database
import config

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is running"}

# -----------------------
# Telegram Bot
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
        [[InlineKeyboardButton("💳 Buy Ticket ¢150", callback_data="buy_ticket")]]
    )

    caption = (
        "🎉 WELCOME to Victory Odds Premium Tips Bot!\n\n"
        "EVERY DAY, you can access a DAILY PREMIUM TICKET with exclusive tips.\n\n"
        "💡 HOW TO USE:\n"
        "1️⃣ Click the button below to purchase today’s ticket\n"
        "2️⃣ Complete the payment securely via Paystack\n"
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
# Buy Ticket Button
# -----------------------
@bot.on_callback_query(filters.regex("buy_ticket"))
async def buy_button(client, callback_query):
    user_id = callback_query.from_user.id

    if database.is_paid(user_id):
        await callback_query.answer("✅ You already purchased today.", show_alert=True)
        return

    # Initialize Paystack transaction
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {config.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": f"user{user_id}@telegram.com",
        "amount": 15000,  # ¢150 in kobo
        "metadata": {"user_id": user_id}
    }

    response = requests.post(url, headers=headers, json=data)
    res = response.json()

    if res.get("status"):
        payment_link = res["data"]["authorization_url"]
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💳 Pay ¢150", url=payment_link)]]
        )
        await callback_query.message.edit_text(
            "Click the button below to pay and get your ticket:",
            reply_markup=keyboard
        )
    else:
        await callback_query.answer("❌ Payment initialization failed.", show_alert=True)

# -----------------------
# Paystack Webhook
# -----------------------
@app.post("/paystack-webhook")
async def paystack_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")

    computed = hmac.new(
        config.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512
    ).hexdigest()

    if computed != signature:
        return {"status": "invalid signature"}

    event = json.loads(payload)

    if event.get("event") == "charge.success":
        user_id = int(event["data"]["metadata"]["user_id"])
        reference = event["data"]["reference"]
        amount = event["data"]["amount"]

        database.mark_paid(user_id)
        database.add_payment(user_id, reference, amount, "success")

        await bot.send_photo(user_id, config.TICKET_URL)

    elif event.get("event") == "charge.failed":
        user_id = int(event["data"]["metadata"]["user_id"])
        await bot.send_message(user_id, "❌ Your payment failed. Please try again.")

    return {"status": "success"}

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
    cursor = database.cursor
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_purchase = date('now')")
    count = cursor.fetchone()[0]
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