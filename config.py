import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

ADMIN_ID = int(os.environ.get("ADMIN_ID"))  # Your Telegram ID

# Selar product checkout link
SELAR_PAYMENT_LINK = "https://selar.com/4w57915757"

# Ticket image (can change daily)
TICKET_IMAGE = os.environ.get("TICKET_URL")

# Selar webhook secret
SELAR_SECRET = "YOUR_SELAR_WEBHOOK_SECRET"