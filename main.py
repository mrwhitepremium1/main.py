import os
import json
import hmac
import hashlib
import requests
from pyrogram import Client, filters
from fastapi import FastAPI, Request
import uvicorn
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
# /start
# -----------------------

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "🔥 Welcome!\n\n"
        "Premium Daily Ticket available.\n"
        "Use /buy to purchase."
    )

# -----------------------
# /buy (Uses Paystack API properly)
# -----------------------

@bot.on_message(filters.command("buy"))
async def buy_ticket(client, message):
    user_id = message.from_user.id

    if database.is_paid(user_id):
        await message.reply_text("✅ You already purchased today.")
        return

    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {config.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": f"user{user_id}@telegram.com",
        "amount": 200000,  # 2000 NGN (amount in kobo)
        "metadata": {
            "user_id": user_id
        }
    }

    response = requests.post(url, headers=headers, json=data)
    res = response.json()

    if res.get("status"):
        payment_link = res["data"]["authorization_url"]
        await message.reply_text(f"💳 Click to pay:\n\n{payment_link}")
    else:
        await message.reply_text("❌ Payment initialization failed.")

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

    if event["event"] == "charge.success":
        user_id = int(event["data"]["metadata"]["user_id"])
        reference = event["data"]["reference"]
        amount = event["data"]["amount"]

        database.mark_paid(user_id)
        database.add_payment(user_id, reference, amount, "success")

        await bot.send_photo(user_id, config.TICKET_URL)

    return {"status": "success"}

# -----------------------
# Startup & Shutdown
# -----------------------

@app.on_event("startup")
async def startup():
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    await bot.stop()