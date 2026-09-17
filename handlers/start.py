from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import register_user_start

def lang_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])

def main_menu_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_new_challenge"), callback_data="menu_new_challenge")],
        [InlineKeyboardButton(t(lang, "btn_about"), callback_data="about")],
        [InlineKeyboardButton(t(lang, "btn_creator"), callback_data="creator")]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user_start(user.id, user.username or "")

    # اگه از لینک مخصوص یه چالش اومده باشه
    if context.args:
        payload = context.args[0]
        if payload.startswith("CH"):
            context.user_data["pending_challenge_id"] = payload[2:]

    await update.message.reply_text(
        t("fa", "choose_language"),
        reply_markup=lang_keyboard()
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data["lang"] = lang

    if context.user_data.get("pending_challenge_id"):
        from handlers.participant import enter_participant_flow
        await enter_participant_flow(update, context)
        return

    await query.edit_message_text(t(lang, "welcome"))
    await query.message.reply_text(
        t(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang)
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    if query.data == "menu_new_challenge":
        from handlers.owner import start_owner_flow
        await start_owner_flow(update, context)
