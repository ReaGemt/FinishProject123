from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to FlowerDelivery bot!')

def order(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    order_details = " ".join(context.args)
    update.message.reply_text(f"Order received: {order_details}")

# Инициализация и запуск бота
updater = Updater("1234567")

updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CommandHandler("order", order))

updater.start_polling()
updater.idle()