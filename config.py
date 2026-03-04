import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
TICKET_URL = os.environ.get("TICKET_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))  # Replace with your Telegram ID