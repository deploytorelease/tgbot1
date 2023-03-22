import logging
import random
import string
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    CallbackContext,
    ConversationHandler,
)

TOKEN = os.environ["TOKEN"]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CREATING, JOINING, IN_FLAT = range(3)

# Хранение квартир и их участников
flats = {}

def generate_flat_id() -> str:
    while True:
        flat_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if flat_id not in flats:
            return flat_id

def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    if any(user_id in flat for flat in flats.values()):
        update.message.reply_text("Вы уже находитесь в квартире.")
        return IN_FLAT

    keyboard = [
        [InlineKeyboardButton("Создать квартиру", callback_data="create_flat")],
        [InlineKeyboardButton("Присоединиться к квартире", callback_data="join_flat")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

    return CREATING

def create_flat(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    flat_id = generate_flat_id()
    flats[flat_id] = [user_id]

    query.edit_message_text(f"Квартира создана. ID квартиры: {flat_id}")
    return IN_FLAT


def join_flat(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    query.edit_message_text("Введите ID квартиры, к которой хотите присоединиться:")

    return JOINING


def process_flat_id(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    flat_id = update.message.text.strip()

    if flat_id not in flats:
        update.message.reply_text("Квартира с таким ID не найдена. Попробуйте еще раз.")
        return JOINING

    flats[flat_id].append(user_id)
    update.message.reply_text(f"Вы присоединились к квартире {flat_id}")

    return IN_FLAT

def open_door(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_data = context.user_data

    if 'opened_doors' not in user_data:
        user_data['opened_doors'] = 0

    user_data['opened_doors'] += 1

    update.message.reply_text(f"Вы открыли дверь {user_data['opened_doors']} раз(а).")

    return IN_FLAT


def change_name(update: Update, context: CallbackContext) -> int:
    new_name = update.message.text.strip()
    user_data = context.user_data

    user_data['name'] = new_name
    update.message.reply_text(f"Ваше имя изменено на {new_name}")

    return IN_FLAT

def show_stats(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_data = context.user_data

    opened_doors = user_data.get('opened_doors', 0)
    update.message.reply_text(f"Вы открыли дверь {opened_doors} раз(а).")

    return IN_FLAT


def show_logs(update: Update, context: CallbackContext) -> int:
    # Здесь вы можете реализовать вывод логов в зависимости от ваших потребностей.
    update.message.reply_text("Просмотр логов еще не реализован.")
    return IN_FLAT

def main():
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(create_flat, pattern="^create_flat$"),
                CallbackQueryHandler(join_flat, pattern="^join_flat$"),
                MessageHandler(Filters.text & ~Filters.command, process_flat_id),
            ],
            IN_FLAT: [
                CommandHandler("opendoor", open_door),
                CommandHandler("changename", change_name),
                CommandHandler("stats", show_stats),
                CommandHandler("logs", show_logs),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()
