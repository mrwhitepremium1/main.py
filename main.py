import os
import asyncio
import hmac
import hashlib
import json
from pyrogram import Client, filters
from fastapi import FastAPI, Request
import uvicorn
import database
import config

# -------------------------------
# FastAPI app (IMPORTANT: must be named app)
# -------------------------------
app = FastAPI()

# -------------------------------
# Telegram Bot
# -------------------------------
bot = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# -------------------------------
# Bot Commands
# -------------------------------

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "🔥 Welcome!\n\n"
        "Daily Premium Ticket is available.\n"
        "Use /buy to purchase today's ticket."
    )

@bot.on_message(filters.command("buy"))
async def buy_ticket(client, message):
    user_id = message.from_user.id

    if database.is_paid(user_id):
        await message.reply_text("✅ You already purchased today’s ticket!")
        return

    payment_link = f"https://paystack.shop/pay/victoryoddsmetadata[user_id]={user_id}"

    await message.reply_text(
        f"💳 Click below to pay:\n\n{payment_link}"
    )

# -------------------------------
# Paystack Webhook
# -------------------------------

@app.post("/paystack-webhook")
async def paystack_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")

    computed_signature = hmac.new(
        config.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512
    ).hexdigest()

    if signature != computed_signature:
        return {"status": "invalid signature"}

    event = json.loads(payload)

    if event["event"] == "charge.success":
        user_id = int(event["data"]["metadata"]["user_id"])
        reference = event["data"]["reference"]

        database.mark_paid(user_id)
        database.add_payment(user_id, reference, event["data"]["amount"], "success")

        # Send ticket automatically
        await bot.send_photo(user_id, config.TICKET_URL)

    return {"status": "success"}

# -------------------------------
# Start Bot When Server Starts
# -------------------------------

@app.on_event("startup")
async def startup():
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    await bot.stop()