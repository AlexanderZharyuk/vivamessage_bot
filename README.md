# vivamessage_bot
Bot for issuing login/registration links for the user, as well as with the possibility of contacting technical support.

## Setting up your development environment of work
To start the bot, you will need to do the following steps:

1. Install the required libraries:
```shell
pip install requirements.txt
```
2. Fill in the config file. It lies along the path `bot/config.ini`:

    You need to fill it according to the example from the repository. If you don't know how to find out your telegram-id, write here: [@userinfobot](https://t.me/userinfobot)


3. Fill in the `.env` file with the following values:
```text
TELEGRAM_BOT_TOKEN=<TELGRAM-BOT-TOKEN> | You can ask @BotFather
API_URL=<YOUR-API-LINK>
API_GUEST_LINK_URL=<YOUR-API-LINK-FOR-GET-GUEST-LINK>
```

## Run the bot
To start the bot, write the following commands in the console:
```shell
cd bot
python3 main.py
```
The bot will issue a warning and run - this is normal.

## Author
- [Alexander Zharyuk](https://github.com/AlexanderZharyuk/)
