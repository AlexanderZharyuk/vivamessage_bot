import configparser
import logging
import os
import sqlite3

from textwrap import dedent
from enum import Enum, auto
from functools import partial

from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton,
                      InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardRemove)
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          MessageHandler, Filters, Updater,
                          CallbackQueryHandler)
from telegram.parsemode import ParseMode
from more_itertools import chunked
from dotenv import load_dotenv

from database_functions import (add_user_phone_number_to_db,
                                get_user_phone_from_db)
from bot_messages import (generate_menu_with_links_message,
                          write_appeal_to_admin)


class States(Enum):
    MAIN_MENU = auto()
    CHOOSE_THEME = auto()
    WRITE_TO_ADMIN = auto()
    APPROVE_APPEAL = auto()
    SEND_PHONE_TO_ADMIN = auto()
    DESCRIPTION = auto()
    USER_CHOICE = auto()
    AUTHORIZE_USER = auto()


logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> States:
    """
    Старт бота - предлагаем пользователю либо войти на сайт,
    либо написать в поддержку.
    """
    greeting_msg = dedent("""\
    Привет!
    Выбери необходимую опцию.
    """).replace("  ", "")

    keyboard_buttons = ["➡️ Войти на сайт", "📧 Написать нам"]
    message_keyboard = list(chunked(keyboard_buttons, 1))
    markup = ReplyKeyboardMarkup(
        message_keyboard,
        resize_keyboard=True,
    )

    given_callback = update.callback_query
    if given_callback:
        given_callback.answer()
        given_callback.delete_message()
        given_callback.message.reply_text(
            text=greeting_msg,
            reply_markup=markup
        )
        return States.MAIN_MENU

    update.message.reply_text(
        text=greeting_msg,
        reply_markup=markup
    )
    return States.MAIN_MENU


def get_main_menu(
        update: Update,
        context: CallbackContext,
        api_url: str,
        api_guest_link_url: str) -> States:
    """
    Предлагаем отправить пользователю номер телефона для прохождения
    регистрации
    """
    if not context.user_data.get("phone_number"):
        chat_id = update.message.chat_id
        phone_number = get_user_phone_from_db(chat_id)
        if not phone_number:
            keyboard_buttons = [
                KeyboardButton(
                    "Отправить номер телефона",
                    request_contact=True)
            ]

            message_keyboard = list(chunked(keyboard_buttons, 2))
            markup = ReplyKeyboardMarkup(
                message_keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
            update.message.reply_text(
                "Для входа или регистрации необходимо отправить ваш номер телефона.",
                reply_markup=markup
            )
            return States.USER_CHOICE

    generate_menu_with_links_message(
        update,
        context,
        api_url,
        api_guest_link_url
    )
    return States.AUTHORIZE_USER


def give_support_themes(
        update: Update,
        context: CallbackContext,
        support_themes: str) -> States:
    """
    Выдаем возможные темы для обращения.
    Берем их из конфига.
    """
    deleted_message = update.message.reply_text(
        "Загружаю список тем...",
        reply_markup=ReplyKeyboardRemove()
    )
    context.bot.delete_message(
        chat_id=deleted_message.chat_id,
        message_id=deleted_message.message_id
    )
    message_keyboard = [
        InlineKeyboardButton(theme, callback_data=theme) for theme
        in support_themes.split(",")
    ]

    markup = InlineKeyboardMarkup(list(chunked(message_keyboard, 2)))
    support_message = dedent("""
    Внимательно выберите тему вашего обращения:
    """).replace("  ", "")
    message = update.message.reply_text(
        text=support_message,
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    context.user_data["message_id"] = message.message_id
    return States.CHOOSE_THEME


def write_description(update: Update, context: CallbackContext) -> States:
    """
    Сохраняем тему обращения в context.user_data и предлагаем пользователю
    описать проблему.
    """
    mail_theme = update.callback_query.data
    context.user_data["mail_theme"] = mail_theme

    message = dedent(f"""\
    Тема обращения: <i>{mail_theme}</i>
    Введите текст вашего обращения:
    """)
    context.bot.edit_message_text(
        text=message,
        chat_id=update.effective_chat.id,
        message_id=context.user_data.get("message_id"),
        parse_mode=ParseMode.HTML
    )
    return States.WRITE_TO_ADMIN


def approve_appeal(update: Update, context: CallbackContext) -> States:
    """
    Сохраняем в context.user_data описание обращения.
    Если до этого пользователь не вводил нигде свой номер - забиваем в БД.
    """

    problem_description = update.message.text
    context.user_data["problem_description"] = problem_description

    message = dedent(f"""\
    <b>Тема:</b> {context.user_data["mail_theme"]}
    <b>Текст:</b> {context.user_data["problem_description"]}
    
    <i>Все верно? Отправляем?</i>
    """)
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Отправить", callback_data="approve"),
                InlineKeyboardButton("Отмена", callback_data="decline")
            ]
        ]
    )

    context.bot.send_message(
        text=message,
        reply_markup=markup,
        chat_id=update.effective_chat.id,
        parse_mode=ParseMode.HTML,
    )
    return States.APPROVE_APPEAL


def send_phone(update: Update,
               context: CallbackContext,
               telegram_admin_id: str) -> States:
    """
    Если телефона пользователя нет в БД - просим его отправить его нам.
    Если телефон есть - отправляем обращение в поддержку.
    """

    if not context.user_data.get("phone_number"):
        chat_id = update.callback_query.message.chat_id
        if not get_user_phone_from_db(chat_id):
            keyboard = [
                [
                    KeyboardButton(
                        "Отправить номер телефона",
                        request_contact=True
                    )
                ]
            ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            context.bot.send_message(
                text="Для обращения необходимо отправить ваш номер телефона.",
                chat_id=chat_id,
                reply_markup=markup
            )
            return States.SEND_PHONE_TO_ADMIN
    write_appeal_to_admin(update, context, telegram_admin_id)
    return States.MAIN_MENU


def write_to_admin(
        update: Update,
        context: CallbackContext,
        telegram_admin_id: str) -> States:
    """
    Добавляем пользователя в БД, если на этом этапе его там нет.
    Обновляем context.user_data, чтобы уменьшить количество запросов к БД.
    """

    if update.message.contact:
        context.user_data["phone_number"] = update.message.contact.phone_number
        add_user_phone_number_to_db(update, context)

    write_appeal_to_admin(update, context, telegram_admin_id)
    return States.MAIN_MENU


def auth_user(
        update: Update,
        context: CallbackContext,
        api_url: str,
        api_guest_link_url: str) -> States:
    """
    Получаем API-Endpoint из внутреннего окружения и делаем запрос.
    """
    user_phone_number = update.message.contact.phone_number
    context.user_data["phone_number"] = user_phone_number
    add_user_phone_number_to_db(update, context)
    generate_menu_with_links_message(
        update,
        context,
        api_url,
        api_guest_link_url=api_guest_link_url
    )

    return States.AUTHORIZE_USER


def incorrect_command(update: Update, context: CallbackContext) -> States:
    """
    Если пользователь неизвестную команду - сообщаем ему об этом.
    """

    message = dedent("""\
    👀 Простите, я вас совсем не понял.
    
    Используйте кнопки ниже для общения со мной. 👇👇👇
    
    <code>(Если не видно команд, переключите клавиатуру, правее поля ввода,\
     кнопочка c 4-мя кругами внутри)</code>
    """).replace("  ", "")
    keyboard_buttons = ["➡️ Войти на сайт", "📧 Написать нам"]
    message_keyboard = list(chunked(keyboard_buttons, 1))
    markup = ReplyKeyboardMarkup(
        message_keyboard,
        resize_keyboard=True,
    )

    update.message.reply_text(
        text=message,
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    return States.MAIN_MENU


if __name__ == '__main__':
    load_dotenv()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    config = configparser.ConfigParser()
    config.read("config.ini")
    telegram_admin_id = config["DEFAULT"]["TELEGRAM_ADMIN_ID"]
    support_themes = config["DEFAULT"]["SUPPORT_THEMES"]

    connection = sqlite3.connect("users.sqlite3")
    cursor = connection.cursor()
    sql_query = """
    CREATE TABLE IF NOT EXISTS Users (telegram_id INT, phone_number CHAR)
    """
    cursor.execute(sql_query)
    connection.commit()
    connection.close()

    telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    api_url = os.environ["API_URL"]
    api_guest_link_url = os.environ["API_GUEST_LINK_URL"]

    updater = Updater(telegram_bot_token, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            States.MAIN_MENU: [
                MessageHandler(
                    Filters.text("➡️ Войти на сайт"),
                    partial(
                        get_main_menu,
                        api_url=api_url,
                        api_guest_link_url=api_guest_link_url
                    )
                ),
                MessageHandler(
                    Filters.text("📧 Написать нам"),
                    partial(
                        give_support_themes,
                        support_themes=support_themes
                    )
                ),
                MessageHandler(
                    Filters.text("В главное меню"), start
                ),
                MessageHandler(
                    Filters.text, incorrect_command
                )
            ],
            States.CHOOSE_THEME: [
                CallbackQueryHandler(
                    write_description
                )
            ],
            States.WRITE_TO_ADMIN: [
                MessageHandler(
                    Filters.text,
                    approve_appeal,
                )
            ],
            States.APPROVE_APPEAL: [
                CallbackQueryHandler(
                    partial(send_phone, telegram_admin_id=telegram_admin_id),
                    pattern="approve"
                ),
                CallbackQueryHandler(
                    start,
                    pattern="decline"
                )
            ],
            States.SEND_PHONE_TO_ADMIN: [
                MessageHandler(
                    Filters.contact,
                    partial(
                        write_to_admin,
                        telegram_admin_id=telegram_admin_id
                    )
                ),
                MessageHandler(
                    Filters.text("Отправить номер телефона"),
                    partial(
                        write_to_admin,
                        telegram_admin_id=telegram_admin_id
                    )
                ),
            ],
            States.USER_CHOICE: [
                MessageHandler(
                    Filters.contact,
                    partial(
                        auth_user,
                        api_url=api_url,
                        api_guest_link_url=api_guest_link_url
                    )
                )
            ],
            States.AUTHORIZE_USER: [
                MessageHandler(
                    Filters.text("Вернуться"), get_main_menu
                ),
                CallbackQueryHandler(
                    start, pattern="back_to_menu"
                )
            ]
        },
        fallbacks=[],
        allow_reentry=True,
        name='bot_conversation'
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()
