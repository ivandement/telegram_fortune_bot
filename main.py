from dotenv import load_dotenv
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 Привет! Я бот-гадалка.\n\n"
        "Я скоро смогу делать расклад по имени, дате рождения и фото."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()