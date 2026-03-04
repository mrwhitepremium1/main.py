from pyrogram import Client, filters
from fastapi import FastAPI, Request
import uvicorn
import hmac
import hashlib
import json
import database
import config
import asyncio
import os

# -------------------------------
# Telegram Bot
# -------------------------------
app = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# /start
@app.on_message(filters.command("start"))
async def start(client, message):
    text = (
        "🔥 Welcome!\n\n"
        "Daily Ticket is available for purchase.\n"
        "Click /buy to get your ticket."
    )
    await message.reply_text(text)

# /buy
@app.on_message(filters.command("buy"))
async def buy_ticket(client, message):
    user_id = message.from_user.id
    if database.is_paid(user_id):
        await message.reply_text("✅ You already purchased your ticket today!")
        return
    
    # Paystack payment link with user_id in metadata
    paystack_link = f"https://paystack.com/pay/your_payment_code_here?metadata[user_id]={user_id}"
    await message.reply_text(f"💳 Click to pay and receive your ticket:\n\n{paystack_link}")

# -------------------------------
# FastAPI Webhook
# -------------------------------
webhook_app = FastAPI()

@webhook_app.post("/paystack-webhook")
async def paystack_webhook(req: Request):
    payload = await req.body()
    signature = req.headers.get("x-paystack-signature")
    
    computed_sig = hmac.new(
        key=bytes(config.PAYSTACK_SECRET_KEY, "utf-8"),
        msg=payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    if signature != computed_sig:
        return {"status": "failed", "reason": "Invalid signature"}
    
    event = json.loads(payload)
    if event['event'] == "charge.success":
        user_id = int(event['data']['metadata']['user_id'])
        reference = event['data']['reference']
        database.mark_paid(user_id)
        database.add_payment(user_id, reference, event['data']['amount'], status="success")
        
        # Send ticket automatically
        await app.send_photo(user_id, config.TICKET_URL)
    
    return {"status": "success"}

# -------------------------------
# Run Bot + Webhook Together
# -------------------------------
async def main():
    await app.start()
    uvicorn_config = uvicorn.Config(webhook_app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    server = uvicorn.Server(uvicorn_config)
    await server.serve()
    await app.stop()

asyncio.run(main())
