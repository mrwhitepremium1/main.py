import os

# Telegram Credentials
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin & Links
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
SELAR_PAYMENT_LINK = "https://selar.com/mrwhite"

# Images (Managed via Railway Variables)
WELCOME_IMAGE = "https://github.com/mrwhitepremium1/main.py/raw/refs/heads/main/IMG_9460.png"
TICKET_IMAGE = os.environ.get("TICKET_URL") 
