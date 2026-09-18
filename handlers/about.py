from telegram import Update
from telegram.ext import ContextTypes
from lang import t
from config import CREATOR_NAME, CREATOR_USERNAME

async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    await query.message.edit_text(t(lang, "about"))

async def creator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    await query.message.reply_text(t(lang, "creator"))
