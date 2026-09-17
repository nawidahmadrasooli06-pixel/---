from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import register_user_start, set_user_language, increment_deep_link_start, get_challenge


def lang_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇦🇫 فارسی", callback_data="lang_fa"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],[InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"), InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]])

def menu_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"new"), callback_data="menu_new")],[InlineKeyboardButton(t(lang,"my_challenges"), callback_data="menu_mine"),InlineKeyboardButton(t(lang,"my_stats"), callback_data="menu_stats")],[InlineKeyboardButton(t(lang,"about"), callback_data="about"),InlineKeyboardButton(t(lang,"creator"), callback_data="creator")]])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    register_user_start(user.id,user.username or "")
    if context.args:
        payload=context.args[0]
        if payload.startswith("CH"):
            cid=payload[2:]
            ch=get_challenge(cid)
            if ch and ch.get("active"):
                context.user_data["pending_challenge_id"]=cid
                increment_deep_link_start(cid)
    await update.message.reply_text(t(context.user_data.get("lang","fa"),"choose_language"),reply_markup=lang_keyboard())

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    lang=q.data.split("_",1)[1]; context.user_data["lang"]=lang; set_user_language(update.effective_user.id,lang)
    if context.user_data.get("pending_challenge_id"):
        from handlers.participant import enter_participant_flow
        await enter_participant_flow(update,context); return
    await q.edit_message_text(t(lang,"welcome")); await q.message.reply_text(t(lang,"main_menu"),reply_markup=menu_keyboard(lang))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); action=q.data
    lang=context.user_data.get("lang","fa")
    if action=="menu_new":
        from handlers.owner import start_owner_flow
        await start_owner_flow(update,context)
    elif action=="menu_mine":
        from handlers.owner import my_challenges
        await my_challenges(update,context)
    elif action=="menu_stats":
        from handlers.owner import my_user_stats
        await my_user_stats(update,context)
