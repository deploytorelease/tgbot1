import os
import sqlite3
from datetime import datetime, timedelta
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

# Инициализация
TOKEN = "6006523726:AAEFSvnANTq06oNq9VKIzKSRu-vq609c-KM"
NAME, JOIN_OR_CREATE, DOOR_ACTION, STATS_CHOICE = range(4)

# Создание базы данных
def create_database():
    conn = sqlite3.connect("flats.db")
    cursor = conn.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            flat_id INTEGER,
            door_opened INTEGER,
            last_opened TIMESTAMP
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS flats (
            id INTEGER PRIMARY KEY,
            flat_id INTEGER
        )"""
    )

    conn.commit()
    conn.close()

# Команды
def start(update: Update, _: CallbackContext):
    update.message.reply_text(
        "Привет! Пожалуйста, введите ваше имя:"
    )
    return NAME

def name(update: Update, context: CallbackContext):
    name = update.message.text
    context.user_data["name"] = name
    reply_keyboard = [["Создать новую квартиру"], ["Присоединиться к квартире"]]
    update.message.reply_text(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup.from_button(reply_keyboard),
    )
    return JOIN_OR_CREATE

def create_flat(update: Update, context: CallbackContext):
    conn = sqlite3.connect("flats.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO flats (flat_id) VALUES (NULL)")
    conn.commit()
    flat_id = cursor.lastrowid

    context.user_data["flat_id"] = flat_id

    cursor.execute(
        "INSERT INTO users (user_id, name, flat_id, door_opened, last_opened) VALUES (?, ?, ?, 0, ?)",
        (update.message.chat_id, context.user_data["name"], flat_id, datetime.now()),
    )
    conn.commit()
    conn.close()

    update.message.reply_text(f"Квартира создана. ID квартиры: {flat_id}")
    return DOOR_ACTION

def join_flat(update: Update, context: CallbackContext):
    update.message.reply_text("Введите ID квартиры, к которой хотите присоединиться:")
    return JOIN_OR_CREATE

def process_flat_id(update: Update, context: CallbackContext):
    flat_id = int(update.message.text)

    conn = sqlite3.connect("flats.db")
    cursor = conn.cursor()

    cursor.execute("SELECT flat_id FROM flats WHERE flat_id=?", (flat_id,))
    flat = cursor.fetchone()

    if flat:
        context.user_data["flat_id"] = flat_id

        cursor.execute(
            "INSERT INTO users (user_id, name, flat_id, door_opened, last_opened) VALUES (?, ?, ?, 0, ?)",
            (update.message.chat_id, context.user_data["name"], flat_id, datetime.now()),
        )
        conn.commit()
        conn.close()
        update.message.reply_text(f"Вы присоединились к квартире с ID: {flat_id}")
        return DOOR_ACTION
    else:
        update.message.reply_text("Квартира с таким ID не найдена. Попробуйте еще раз:")
        return JOIN_OR_CREATE

def door_action(update: Update, _: CallbackContext):
    reply_keyboard = [
        [InlineKeyboardButton("Я открою", callback_data="open")],
        [InlineKeyboardButton("Я открыл", callback_data="opened")],
        [InlineKeyboardButton("Статистика", callback_data="stats")],
    ]
    update.message.reply_text(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(reply_keyboard),
    )
    return DOOR_ACTION

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    conn = sqlite3.connect("flats.db")
    cursor = conn.cursor()

    if query.data == "open":
        user = cursor.execute(
            "SELECT name FROM users WHERE user_id=?",
            (update.effective_chat.id,),
        ).fetchone()
        name = user[0] if user else "Неизвестный"

        flat_id = context.user_data["flat_id"]

        users_in_flat = cursor.execute(
            "SELECT user_id FROM users WHERE flat_id=?", (flat_id,)
        ).fetchall()

        for user_id in users_in_flat:
            if user_id[0] != update.effective_chat.id:
                context.bot.send_message(
                    user_id[0],
                    f"Пользователь {name} собирается открыть дверь.",
                )

        query.edit_message_text("Вы сообщили о своем намерении открыть дверь.")
    elif query.data == "opened":
        cursor.execute(
            "UPDATE users SET door_opened = door_opened + 1, last_opened = ? WHERE user_id=?",
            (datetime.now(), update.effective_chat.id),
        )
        conn.commit()
        query.edit_message_text("Вы успешно открыли дверь.")
    elif query.data == "stats":
        reply_keyboard = [
            [InlineKeyboardButton("Всего", callback_data="total")],
            [InlineKeyboardButton("За неделю", callback_data="week")],
            [InlineKeyboardButton("За месяц", callback_data="month")],
        ]
        query.edit_message_text(
            "Выберите период для статистики:",
            reply_markup=InlineKeyboardMarkup(reply_keyboard),
        )
    return DOOR_ACTION

def show_stats(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    period = query.data

    if period == "total":
        time_condition = ""
    elif period == "week":
        time_condition = "AND last_opened >= ?"
        time_param = (datetime.now() - timedelta(days=7),)
    elif period == "month":
        time_condition = "AND last_opened >= ?"
        time_param = (datetime.now() - timedelta(days=30),)

    conn = sqlite3.connect("flats.db")
    cursor = conn.cursor()

    flat_id = context.user_data["flat_id"]

    users = cursor.execute(
        f"SELECT name, door_opened FROM users WHERE flat_id=? {time_condition}",
        (flat_id,) + (time_param if time_condition else ()),    ).fetchall()
    conn.close()

    if users:
        stats = "\n".join([f"{user[0]}: {user[1]} раз" for user in users])
        query.edit_message_text(f"Статистика открытия двери:\n{stats}")
    else:
        query.edit_message_text("Нет данных для выбранного периода.")

    return DOOR_ACTION

def cancel(update: Update, _: CallbackContext):
    update.message.reply_text("До свидания!")
    return ConversationHandler.END

def main():
    create_database()
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(Filters.text, name)],
            JOIN_OR_CREATE: [
                MessageHandler(Filters.regex("^Создать новую квартиру$"), create_flat),
                MessageHandler(Filters.regex("^Присоединиться к квартире$"), join_flat),
                MessageHandler(Filters.text, process_flat_id),
            ],
            DOOR_ACTION: [
                MessageHandler(Filters.text, door_action),
                CallbackQueryHandler(button_callback),
                CallbackQueryHandler(show_stats, pattern="^(total|week|month)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()

if __name__ == "__main__":
    main()