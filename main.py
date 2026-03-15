@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = (
        "👋 **Welcome to the Signal Service!**\n\n"
        "The bot is currently under maintenance. To get your access ticket immediately:\n\n"
        "🔗 **Pay via Selar:** [INSERT YOUR LINK]\n"
        "📩 **DM for Approval:** @[YOUR_USERNAME]\n\n"
        "Please send your proof of payment to the admin above for manual activation!"
    )
    await event.respond(msg)
