# --- ADD THIS TO YOUR MENU COMMANDS SECTION ---
@client.on(events.NewMessage(pattern='/price'))
async def price(event):
    price_text = (
        "💰 **Mr. White Official Price List**\n\n"
        "⭐ **Single Ticket (24h Access):** 50 GHS\n"
        "🔥 **Weekly Pass (7 Days):** 250 GHS\n"
        "💎 **VIP Monthly (30 Days):** 800 GHS\n\n"
        "✅ **What you get:**\n"
        "• 100% Guaranteed Correct Scores\n"
        "• Daily Updates\n"
        "• 24/7 Support\n\n"
        "Click /start to pay and get your ticket now!"
    )
    await event.reply(price_text)

# --- UPDATED AUTO-REPLY (With Price Button) ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_reply(event):
    if event.text.startswith('/'): return
    if event.sender_id == config.ADMIN_ID: return

    reply_text = (
        "🤖 **Mr. White Official Assistant**\n\n"
        "I am an automated system. How can I help you today?"
    )
    
    # Adding a Price button directly to the auto-reply
    buttons = [
        [Button.inline("🎫 View Ticket", data="show_start_logic")],
        [Button.inline("💰 View Price List", data="show_price_logic")]
    ]
    await event.reply(reply_text, buttons=buttons)

# --- CALLBACKS FOR AUTO-REPLY BUTTONS ---
@client.on(events.CallbackQuery(data="show_price_logic"))
async def show_price_btn(event):
    await event.answer() # Stops loading spinner
    # Redirects to the price command logic
    await price(event)
