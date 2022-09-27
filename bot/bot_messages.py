from datetime import datetime

from textwrap import dedent

import requests

from more_itertools import chunked
from telegram import (Update, InlineKeyboardButton,
                      InlineKeyboardMarkup, ReplyKeyboardRemove,
                      ParseMode, ReplyKeyboardMarkup)
from telegram.ext import CallbackContext

from database_functions import get_user_phone_from_db


def generate_menu_with_links_message(
        update: Update,
        context: CallbackContext,
        api_url: str,
        api_guest_link_url: str) -> None:
    """
    Функция для генерации сообщения с ссылками пользователю
    """

    chat_id = update.message.chat_id
    username = update.message.from_user.name
    if update.message.contact:
        user_phone_number = update.message.contact.phone_number
    else:
        if not context.user_data.get("phone_number"):
            context.user_data["phone_number"] = get_user_phone_from_db(chat_id)
        user_phone_number = context.user_data["phone_number"]

    payload = {
        "phone": user_phone_number,
        "chat_id": chat_id,
        "username": username
    }
    response = requests.post(api_url, data=payload)
    response.raise_for_status()

    response_to_user = response.json()
    link_to_auth = response_to_user.get("login")
    message = dedent(f"""\
                🔗 Вот ваша ссылка для входа на сайт:
                <i>(действует 5 мин)</i>
                """)

    keyboard_buttons = [
        [InlineKeyboardButton(url=link_to_auth, text="Ссылка для входа")],
    ]

    if not response_to_user.get("login"):
        link_to_auth = response_to_user.get("register")

        response = requests.get(api_guest_link_url)
        response.raise_for_status()

        response_to_user = response.json()
        guest_link = response_to_user["url"]

        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    url=link_to_auth,
                    text="Cсылка для регистрации"
                )
            ],
            [
                InlineKeyboardButton(url=guest_link, text="Гостевая ссылка")
            ],
        ]
        message = dedent(f"""\
                            📱 По вашему номеру телефона не найдено регистрации.

                            Ниже указана ссылка на <b>регистрацию</b>
                            <i>(действует 5 мин)</i>
                            """)

    keyboard_buttons.append([InlineKeyboardButton(
        callback_data="back_to_menu",
        text="Главное меню"
    )])

    markup = InlineKeyboardMarkup(
        inline_keyboard=keyboard_buttons,
        resize_keyboard=True
    )

    deleted_message = update.message.reply_text(
        "Создаю ссылку...",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )
    context.bot.delete_message(
        message_id=deleted_message.message_id,
        chat_id=deleted_message.chat_id
    )
    update.message.reply_text(
        message,
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )


def write_appeal_to_admin(
        update: Update,
        context: CallbackContext,
        telegram_admin_id: str) -> None:
    """
    Функция по написанию обращения к админу.
    """
    if not update.callback_query:
        chat_id = update.message.from_user.id
        username = update.message.from_user.username
    else:
        chat_id = update.callback_query.message.chat_id
        username = update.callback_query.message.chat.username

    if not context.user_data.get("phone_number"):
        context.user_data["phone_number"] = get_user_phone_from_db(chat_id)

    user_appeal_message = dedent(f"""\
        --------------------
        Дата и Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        chat id: {chat_id}
        username: {username}
        phone: {context.user_data.get("phone_number")}
        Тема:  {context.user_data.get("mail_theme")}
        Текст сообщения: {context.user_data.get("problem_description")}
        ---------------------
        """).replace("  ", "")
    context.bot.send_message(
        chat_id=telegram_admin_id,
        text=user_appeal_message
    )

    greeting_msg = dedent("""\
       Ваше обращение отправлено!
       Выберите необходимую опцию.
       """).replace("  ", "")

    keyboard_buttons = ["➡️ Войти на сайт", "📧 Написать нам"]
    message_keyboard = list(chunked(keyboard_buttons, 1))
    markup = ReplyKeyboardMarkup(
        message_keyboard,
        resize_keyboard=True,
    )
    context.bot.send_message(
        text=greeting_msg,
        chat_id=chat_id,
        reply_markup=markup
    )
