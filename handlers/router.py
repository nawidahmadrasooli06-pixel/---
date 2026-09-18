from telegram import Update
from telegram.ext import ContextTypes
from handlers.owner import (
    receive_title, receive_channel, receive_owner_username, receive_custom_date, receive_time,
    receive_duration, receive_winners, receive_prize, receive_rules, receive_stars_rate,
)
from handlers.participant import receive_name, receive_age, receive_city, receive_photo, receive_report_text

TEXT_STATE_HANDLERS = {
    "await_title": receive_title,
    "await_channel": receive_channel,
    "await_owner_username": receive_owner_username,
    "await_custom_date": receive_custom_date,
    "await_time": receive_time,
    "await_duration": receive_duration,
    "await_winners": receive_winners,
    "await_prize": receive_prize,
    "await_rules": receive_rules,
    "await_stars_rate": receive_stars_rate,
    "await_name": receive_name,
    "await_age": receive_age,
    "await_city": receive_city,
    "await_report_text": receive_report_text,
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    handler = TEXT_STATE_HANDLERS.get(state)
    if handler:
        await handler(update, context)


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "await_photo":
        await receive_photo(update, context)
