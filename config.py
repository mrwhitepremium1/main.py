import os

# Telegram bot
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

# Admins
ADMIN_IDS = [int(os.environ.get("ADMIN_ID"))]

# Payment
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")

# Ticket (image or PDF URL)
TICKET_URL = os.environ.get("TICKET_URL")
