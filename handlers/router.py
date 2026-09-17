from telegram import Update
from telegram.ext import ContextTypes
from handlers.owner import receive_title,receive_channel,receive_owner,receive_start,receive_duration,receive_winners,receive_prize,receive_rules,receive_rate
from handlers.participant import receive_name,receive_residence,receive_photo
HANDLERS={"await_title":receive_title,"await_channel":receive_channel,"await_owner":receive_owner,"await_start":receive_start,"await_duration":receive_duration,"await_winners":receive_winners,"await_prize":receive_prize,"await_rules":receive_rules,"await_rate":receive_rate,"await_name":receive_name,"await_residence":receive_residence}
async def text_router(update:Update,context:ContextTypes.DEFAULT_TYPE):
    h=HANDLERS.get(context.user_data.get("state"));
    if h: await h(update,context)
async def photo_router(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state")=="await_photo": await receive_photo(update,context)
