import os
import json
import hmac
import hashlib
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import database
import config

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI()

# Root endpoint for Railway health check
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
# /start Command — Shows Button
# -----------------------
@bot.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Buy Ticket ¢150", callback_data="buy_ticket")]
        ]
    )
    await message.reply_text(
        "🔥 Welcome!\n\n"
        "Premium Daily Ticket available.\n"
        "Click the button below to purchase.",
        reply_markup=keyboard
    )

# -----------------------
# Callback Query — Buy Button
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
        "amount": 15000,  # 150 Naira in kobo
        "metadata": {"user_id": user_id}
    }

    response = requests.post(url, headers=headers, json=data)
    res = response.json()

    if res.get("status"):
        payment_link = res["data"]["authorization_url"]

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💳 Pay ¢150", url=payment_link)]
            ]
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

    # Verify signature
    computed = hmac.new(
        config.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512
    ).hexdigest()

    if computed != signature:
        return {"status": "invalid signature"}

    event = json.loads(payload)

    # Successful payment
    if event.get("event") == "charge.success":
        user_id = int(event["data"]["metadata"]["user_id"])
        reference = event["data"]["reference"]
        amount = event["data"]["amount"]

        # Mark paid in database
        database.mark_paid(user_id)
        database.add_payment(user_id, reference, amount, "success")

        # Send ticket automatically
        await bot.send_photo(user_id, config.TICKET_URL)

    return {"status": "success"}

# -----------------------
# Startup & Shutdown Events
# -----------------------
@app.on_event("startup")
async def startup():
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    await bot.stop()