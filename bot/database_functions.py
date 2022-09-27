import sqlite3


from typing import Union

from telegram import Update
from telegram.ext import CallbackContext


def add_user_phone_number_to_db(
        update: Update,
        context: CallbackContext) -> None:
    """
    Записываем пользователя в БД и в context_data для уменьшения количества
    обращений к БД
    """
    chat_id = update.message.from_user.id
    if get_user_phone_from_db(chat_id):
        return

    user_phone_number = update.message.contact.phone_number
    context.user_data["phone_number"] = user_phone_number

    connection = sqlite3.connect("users.sqlite3")
    cursor = connection.cursor()

    params = chat_id, user_phone_number

    cursor.execute("INSERT INTO Users VALUES (?, ?)", params)
    connection.commit()
    connection.close()


def get_user_phone_from_db(chat_id: int) -> Union[dict | None]:
    """
    Отдаем инфу о пользователе из БД. Если его нет в БД - возвращаем NONE
    """
    connection = sqlite3.connect("users.sqlite3")
    cursor = connection.cursor()

    sql_query = "SELECT * FROM Users WHERE telegram_id == ?"
    cursor.execute(sql_query, (chat_id, ))
    user = cursor.fetchone()

    if not user:
        return None

    user_id, user_phone_number = user
    return user_phone_number


