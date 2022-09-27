# vivamessage_bot
Бот для выдачи ссылок на вход/регистрацию для пользователя, а также с возможностью обращения в тех.поддержку.

## Начало работы
Для запуска бота вам потребуется проделать следующие шаги:

1. Установить необходимые библиотеки:
```shell
pip install requirements.txt
```
2. Заполнить конфиг файл. Он лежит по пути `bot/config.ini`:

    Его вам нужно заполнить по примеру из репозитория. Если не знаете, как узнать свой telegram-id, напишите сюда: [@userinfobot](https://t.me/userinfobot)


3. Заполнить `.env`-файл со следующими значениями:
```text
TELEGRAM_BOT_TOKEN=<TELGRAM-BOT-TOKEN> | Можно узнать у @BotFather
API_URL=<YOUR-API-LINK>
API_GUEST_LINK_URL=<YOUR-API-LINK-FOR-GET-GUEST-LINK>
```

## Запуск бота
Для запуска бота напишите следующие команды в консоли:
```shell
cd bot
python3 main.py
```
Бот выдаст предупреждение и запустится - это нормально.

## Автор
- [Alexander Zharyuk](https://github.com/AlexanderZharyuk/)
