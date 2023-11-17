import os
import asyncio
import logging
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from taskernet import (
    get_inline_data,
    get_message_url_and_button_for,
    get_description,
    TASKERNET_URL,
)
from utils import log
from aiohttp import web


BOT_TOKEN = os.environ.get("BOT_TOKEN")
APP_ADDRESS = os.environ.get("APP_ADDRESS")
WEBHOOK_PORT = os.environ.get("PORT")
WEBHOOK_PATH = f"/{BOT_TOKEN}/"
WEBHOOK_URL = f"{APP_ADDRESS}:{WEBHOOK_PORT}" + WEBHOOK_PATH
BOT_USERNAME = telebot.TeleBot(BOT_TOKEN).get_me().username

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)


bot = AsyncTeleBot(BOT_TOKEN)
app = web.Application()


async def redirect_to_bot(request):
    return web.HTTPFound(f"https://t.me/{BOT_USERNAME}")


# Process webhook calls
async def handle(request):
    if request.match_info.get("token") == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        tasks = [
            asyncio.ensure_future(bot.process_new_updates([update])),
            asyncio.sleep(1)
        ]
        await asyncio.gather(*tasks)
        return web.Response()
    else:
        return web.Response(status=403)


# send welcome message
async def send_welcome(message):
    buttons = types.InlineKeyboardMarkup()
    btn_here = types.InlineKeyboardButton(
        text="Go inline here", switch_inline_query_current_chat=""
    )
    btn_there = types.InlineKeyboardButton(
        text="Go inline in a chat",
        switch_inline_query_chosen_chat=types.SwitchInlineQueryChosenChat(
            query="",
            allow_bot_chats=False,
            allow_channel_chats=True,
            allow_group_chats=True,
            allow_user_chats=True,
        ),
    )
    buttons.row(btn_here, btn_there)
    await bot.reply_to(
        message,
        text=f"Hello {message.from_user.first_name},\nThis bot works only in inline mode.",
        reply_markup=buttons,
    )


# handle commands
@bot.message_handler(commands=["help", "start"])
async def handle_commands(message):
    await send_welcome(message)


# All text message handled here
@bot.message_handler(func=lambda message: True)
async def received_message(message):
    # don't reply to own messages
    if message.via_bot is not None and message.via_bot.username == BOT_USERNAME:
        exit
    else:
        await send_welcome(message)


# handle inline queries
@bot.inline_handler(func=lambda query: len(query.query) > 0)
async def query_text(inline_query):
    id = str(inline_query.id)
    query = inline_query.query
    log(f"searching for {query}")
    results = await get_inline_data(query)
    if results:
        button = None
    else:
        button = types.InlineQueryResultsButton(
            "No result found!", start_parameter="help"
        )
        log("No Result Found for " + query)
    await bot.answer_inline_query(id, results, button=button)


# update chosen result with description
@bot.chosen_inline_handler(func=lambda chosen_inline_result: True)
async def update_message_with_description(chosen):
    if not chosen.query.startswith(TASKERNET_URL):
        id = chosen.inline_message_id
        message, url, buttons = get_message_url_and_button_for(chosen.result_id)
        if not url:
            log("failed to get url for chosen query")
            exit
        description = await get_description(str(url))
        text = str(message) + "\n\n" + description
        await bot.edit_message_text(
            text=text, inline_message_id=id, parse_mode="Markdown", reply_markup=buttons
        )


async def setup():
    hasWebhook = await bot.get_webhook_info()
    if hasWebhook: 
        log("Starting up: removing old webhook")
        await bot.remove_webhook()
    log("Starting up: setting webhook")
    await bot.set_webhook(url=WEBHOOK_URL)
    app = web.Application()
    app.router.add_post("/{token}/", handle)
    app.router.add_get("/", redirect_to_bot)
    log("webhook set")
    return app