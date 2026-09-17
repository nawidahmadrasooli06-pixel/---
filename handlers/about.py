
from telegram import Update
from telegram.ext import ContextTypes
from lang import t

async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(t(lang, "about_text"))

async def creator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(t(lang, "creator_text"))
