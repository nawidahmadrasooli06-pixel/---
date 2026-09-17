from telegram import Update
from telegram.ext import ContextTypes
from handlers.owner import (
    receive_channel, receive_winners_count, receive_prize,
    receive_start_time, receive_end_time, receive_stars_rate
)
from handlers.participant import (
    receive_name, receive_age, receive_city, receive_photo
)

TEXT_STATE_HANDLERS = {
    "await_channel": receive_channel,
    "await_winners_count": receive_winners_count,
    "await_prize": receive_prize,
    "await_start_time": receive_start_time,
    "await_end_time": receive_end_time,
    "await_stars_rate": receive_stars_rate,
    "await_name": receive_name,
    "await_age": receive_age,
    "await_city": receive_city,
}

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    handler = TEXT_STATE_HANDLERS.get(state)
    if handler:
        await handler(update, context)

async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state == "await_photo":
        await receive_photo(update, context)
