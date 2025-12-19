import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

# --- Configuration ---
TELEGRAM_BOT_TOKEN = "8012133467:AAH5kLMXe2iaXZ4gdePkx8-nCy7B-4oThv4"
GENERATE_API_URL = "http://127.0.0.1:8901/generate"

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("請輸入有關職業安全的法律問題，我會依照法條回答問題。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Send "Typing..." action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # We also need a timeout here for the call to YOUR api
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GENERATE_API_URL, 
            params={"user_text": user_text}
        )
        response.raise_for_status()
        ai_reply = response.json()

    await update.message.reply_text(
        str(ai_reply),
        reply_to_message_id=update.message.message_id,
    )

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text(
            "Sorry, something went wrong.\n"
            # f"Update \n{update} \n\ncaused error\n{context.error}",
            f"\n{context.error}",
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        pass


if __name__ == '__main__':
    # --- YOUR REQUESTED SETTINGS ---
    # Define timeouts for Telegram communication
    t_request = HTTPXRequest(
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0
    )

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(t_request) # Apply timeouts
        .build()
    )

    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(text_handler)

    start_handler = MessageHandler(filters.COMMAND, start)
    application.add_handler(start_handler)

    application.add_error_handler(error)

    print("Telegram Bot is polling with concurrent updates...")
    
    # Enable Concurrency here
    application.run_polling(allowed_updates=Update.ALL_TYPES)
