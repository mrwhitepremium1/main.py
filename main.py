import os
import asyncio
from pyrogram import Client
import uvicorn
import config
import database
from fastapi import FastAPI

# Telegram bot
app = Client(
    "ticket_bot",
    api_id=int(config.API_ID),
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# FastAPI webhook
webhook_app = FastAPI()

# -------------------------------
# Your bot handlers go here (start, buy, etc.)
# -------------------------------

# -------------------------------
# Run Bot + Webhook
# -------------------------------
async def start_bot_and_webhook():
    await app.start()
    # Run FastAPI server
    config_uvicorn = uvicorn.Config(webhook_app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    server = uvicorn.Server(config_uvicorn)
    await server.serve()
    await app.stop()

# This ensures it works even if an event loop is already running
loop = asyncio.get_event_loop()
loop.create_task(start_bot_and_webhook())