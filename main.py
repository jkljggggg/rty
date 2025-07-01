import requests
import random
import time
import re
from faker import Faker
from telegram import Update
# Corrected imports: Using Application and filters, removed Updater
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# --- Constants and Setup ---
TOKEN = "7770310160:AAF4gzYzIop54012jUDGAqSx1G0kMX8ZDPU"
fake = Faker()
USERNAME, = range(1)

# --- Helper Functions ---

def load_reports():
    """Loads report messages from a file."""
    try:
        with open("report.txt", "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []

def is_valid_username(username):
    """Checks if a Telegram username exists."""
    try:
        response = requests.get(f"https://t.me/{username}", timeout=5)
        return "tgme_page_title" in response.text
    except requests.RequestException:
        return False

def generate_data(username, message):
    """Generates fake user data for the report form."""
    name = fake.name()
    email_user = fake.user_name()
    email_domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "protonmail.com"])
    email = f"{email_user}@{email_domain}"
    number = '7' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
    final_msg = message.replace("@username", f"@{username}")
    return {
        "message": final_msg,
        "legal_name": name,
        "email": email,
        "phone": number,
        "setln": ""
    }, name, email, number, final_msg

def load_proxies():
    """Loads a list of proxies from a file."""
    try:
        with open("NG.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def send_data(data, proxy=None):
    """Sends the report data to Telegram's support form."""
    headers = {
        "Host": "telegram.org",
        "Origin": "https://telegram.org",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Referer": "https://telegram.org/support"
    }
    try:
        proxies = None
        if proxy:
            proxies = {'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'}
        
        res = requests.post("https://telegram.org/support", data=data, headers=headers, proxies=proxies, timeout=10)
        success = "Thank you" in res.text or res.status_code == 200
        return success, proxy if proxy else "direct"
    except requests.RequestException:
        return False, proxy if proxy else "direct"

# --- Bot Handlers ---

async def start(update: Update, context: CallbackContext):
    """Starts the conversation and asks for the username."""
    await update.message.reply_text(
        "👋 **Welcome!**\n\nPlease enter the target channel/group username (without @)."
    )
    return USERNAME

async def handle_username(update: Update, context: CallbackContext):
    """Handles the user input, validates it, and starts the reporting process."""
    username = update.message.text.strip().lstrip('@')
    context.user_data["username"] = username

    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await update.message.reply_text("❌ **Invalid Format**: Usernames must be 5-32 characters long and contain only letters, numbers, and underscores.")
        return ConversationHandler.END

    await update.message.reply_text("🔍 Checking if the username exists...")
    if not is_valid_username(username):
        await update.message.reply_text("❌ **Not Found**: This username does not appear to exist on Telegram.")
        return ConversationHandler.END

    await update.message.reply_text("✅ **Username Validated**: Starting the reporting process. This may take some time...")

    reports = load_reports()
    if not reports:
        await update.message.reply_text("❌ **Error**: `report.txt` is empty or not found. Please create it and add report messages.")
        return ConversationHandler.END

    total = len(reports)
    success_count = 0
    progress_message = await update.message.reply_text("📤 Starting reports...")

    report_log = []
    proxies = load_proxies()
    proxy_index = 0
    
    for i, msg in enumerate(reports):
        form_data, name, email, number, final_msg = generate_data(username, msg)
        
        proxy_to_use = None
        if proxies:
            proxy_to_use = proxies[proxy_index]

        success, used_proxy = send_data(form_data, proxy_to_use)
        
        if success:
            success_count += 1
            report_log.append(f"Report {i+1}:\n- Name: {name}\n- Email: {email}\n- Phone: {number}\n- Proxy: {used_proxy}\n- Message: {final_msg}\n---\n")
        
        if proxies:
            proxy_index = (proxy_index + 1) % len(proxies)
        
        await asyncio.sleep(2) # Use asyncio.sleep in async functions

        percent = int(((i + 1) / total) * 100)
        progress_bar = "█" * (percent // 10) + "▒" * (10 - (percent // 10))
        
        try:
            await progress_message.edit_text(
                f"📊 **Progress**: [{progress_bar}] {percent}%\n"
                f"📤 **Sent**: {i+1}/{total}\n"
                f"✅ **Successful**: {success_count}"
            )
        except: # Avoid crashing on Telegram's "message is not modified" error
            pass
        
        # Save logs periodically
        if len(report_log) > 0 and len(report_log) % 50 == 0:
            file_path = f"reports_{username}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(report_log)
            
            await update.message.reply_document(
                document=open(file_path, "rb"),
                caption=f"📋 Report details for the first {success_count} successful reports."
            )

    await progress_message.edit_text(
        f"✅ **Complete!**\n\n"
        f"📊 **Progress**: [██████████] 100%\n"
        f"📨 **Total Successful Reports**: {success_count}/{total}"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext):
    """Cancels the current operation."""
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# --- Main Application Runner ---

def main():
    """Sets up and runs the Telegram bot."""
    # Use Application.builder() instead of Updater
    app = Application.builder().token(TOKEN).build()

    # Define the conversation handler with entry and state points
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # Use the new 'filters' module with uppercase attributes
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Add the handler to the application
    app.add_handler(conv_handler)

    # Use run_polling() to start the bot
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    import asyncio # Import asyncio for async sleep
    main()