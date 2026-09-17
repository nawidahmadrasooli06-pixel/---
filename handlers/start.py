from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import register_user_start, increment_deep_start, get_challenge, is_blocked
from config import ADMIN_ID


def lang_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇦🇫 🇮🇷 فارسی", callback_data="lang_fa"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]])


def main_menu_keyboard(lang, user_id=None):
    rows = [
        [InlineKeyboardButton(t(lang, "new"), callback_data="menu_new")],
        [InlineKeyboardButton(t(lang, "owner_panel"), callback_data="menu_owner")],
        [InlineKeyboardButton(t(lang, "my_stats"), callback_data="menu_stats")],
        [InlineKeyboardButton(t(lang, "my_challenges"), callback_data="menu_challenges"), InlineKeyboardButton(t(lang, "report"), callback_data="menu_report")],
        [InlineKeyboardButton(t(lang, "about"), callback_data="about"), InlineKeyboardButton(t(lang, "creator"), callback_data="creator")],
    ]
    if user_id == ADMIN_ID:
        rows.append([InlineKeyboardButton("🛡 Super Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user_start(user.id, user.username or "")
    if is_blocked(user.id):
        await update.message.reply_text("⛔ دسترسی این حساب به ربات محدود شده است.")
        return
    context.user_data.clear()
    if context.args:
        payload = context.args[0]
        if payload.startswith("CH"):
            challenge_id = payload[2:]
            if get_challenge(challenge_id):
                context.user_data["pending_challenge_id"] = challenge_id
                from database import challenges
                from bson import ObjectId
                challenges.update_one({"_id": ObjectId(challenge_id)}, {"$inc": {"deep_link_starts": 1}, "$addToSet": {"deep_link_users": user.id}})
    await update.message.reply_text(t("fa", "choose_language"), reply_markup=lang_keyboard())


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_", 1)[1]
    context.user_data["lang"] = lang
    if context.user_data.get("pending_challenge_id"):
        from handlers.participant import enter_participant_flow
        await query.message.reply_text(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang, query.from_user.id))
        await enter_participant_flow(update, context)
        return
    await query.edit_message_text(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get("lang", "fa")
    if data == "menu_new":
        from handlers.owner import start_owner_flow
        await start_owner_flow(update, context)
    elif data == "menu_owner":
        from handlers.owner import owner_panel
        await owner_panel(update, context)
    elif data == "menu_stats":
        from handlers.participant import my_stats
        await my_stats(update, context)
    elif data == "menu_challenges":
        from handlers.owner import my_challenges
        await my_challenges(update, context)
    elif data == "menu_report":
        from handlers.participant import report_panel
        await report_panel(update, context)
