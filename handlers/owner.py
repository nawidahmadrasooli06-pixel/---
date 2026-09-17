from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from lang import t
from database import create_challenge
from config import BOT_TOKEN
import re

CHANNEL, WINNERS_COUNT, PRIZE, START_TIME, END_TIME, STARS_TOGGLE, STARS_RATE, PREVIEW = range(8)

async def start_owner_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["new_challenge"] = {}
    await update.callback_query.message.reply_text(t(lang, "ask_channel"))
    return CHANNEL

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    channel = update.message.text.strip()
    try:
        chat = await context.bot.get_chat(channel)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text(t(lang, "bot_not_admin"))
            return CHANNEL
    except Exception:
        await update.message.reply_text(t(lang, "bot_not_admin"))
        return CHANNEL

    context.user_data["new_challenge"]["channel_id"] = chat.id
    context.user_data["new_challenge"]["channel_username"] = chat.username
    context.user_data["new_challenge"]["channel_link"] = f"https://t.me/{chat.username}" if chat.username else ""
    await update.message.reply_text(t(lang, "ask_winners_count"))
    return WINNERS_COUNT

async def receive_winners_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        count = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(t(lang, "ask_winners_count"))
        return WINNERS_COUNT
    context.user_data["new_challenge"]["winners_count"] = count
    context.user_data["new_challenge"]["prizes"] = []
    context.user_data["prize_rank"] = 1
    await update.message.reply_text(t(lang, "ask_prize", rank=1))
    return PRIZE

async def receive_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    prizes = context.user_data["new_challenge"]["prizes"]
    prizes.append(update.message.text.strip())
    rank = context.user_data["prize_rank"] + 1
    total = context.user_data["new_challenge"]["winners_count"]
    if rank <= total:
        context.user_data["prize_rank"] = rank
        await update.message.reply_text(t(lang, "ask_prize", rank=rank))
        return PRIZE
    await update.message.reply_text(t(lang, "ask_start_time"))
    return START_TIME

def parse_dt(text):
    from datetime import datetime
    return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")

async def receive_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        context.user_data["new_challenge"]["start_time"] = parse_dt(update.message.text)
    except ValueError:
        await update.message.reply_text(t(lang, "ask_start_time"))
        return START_TIME
    await update.message.reply_text(t(lang, "ask_end_time"))
    return END_TIME

async def receive_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        context.user_data["new_challenge"]["end_time"] = parse_dt(update.message.text)
    except ValueError:
        await update.message.reply_text(t(lang, "ask_end_time"))
        return END_TIME
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "btn_yes"), callback_data="stars_yes"),
        InlineKeyboardButton(t(lang, "btn_no"), callback_data="stars_no")
    ]])
    await update.message.reply_text(t(lang, "ask_stars"), reply_markup=kb)
    return STARS_TOGGLE

async def receive_stars_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "stars_yes":
        context.user_data["new_challenge"]["stars_enabled"] = True
        await query.message.reply_text(t(lang, "ask_stars_rate"))
        return STARS_RATE
    context.user_data["new_challenge"]["stars_enabled"] = False
    context.user_data["new_challenge"]["stars_rate"] = 0
    return await show_preview(update, context)

async def receive_stars_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        rate = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(t(lang, "ask_stars_rate"))
        return STARS_RATE
    context.user_data["new_challenge"]["stars_rate"] = rate
    return await show_preview(update, context)

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    data = context.user_data["new_challenge"]
    prizes_text = "\n".join([f"🏆 {i+1}: {p}" for i, p in enumerate(data["prizes"])])
    preview = (
        f"🌟 چالش لایکی 🌟\n\n"
        f"شروع: {data['start_time']}\nپایان: {data['end_time']}\n\n"
        f"{prizes_text}\n\n"
        f"⭐️ استارز: {'فعال' if data.get('stars_enabled') else 'غیرفعال'}\n\n"
        f"کانال: {data.get('channel_link','')}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "btn_confirm"), callback_data="preview_confirm"),
        InlineKeyboardButton(t(lang, "btn_edit"), callback_data="preview_cancel")
    ]])
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text(t(lang, "preview_ready") + "\n\n" + preview, reply_markup=kb)
    return PREVIEW

async def confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "preview_cancel":
        await query.message.reply_text("لغو شد. دوباره از منو شروع کن.")
        return ConversationHandler.END

    data = context.user_data["new_challenge"]
    owner_id = update.effective_user.id
    challenge_id = create_challenge(owner_id, data["channel_id"], data.get("channel_link", ""), data)

    reg_link = f"https://t.me/{context.bot.username}?start=CH{challenge_id}"
    banner = (
        f"🌟 چالش لایکی جدید شروع شد 🌟\n\n"
        + "\n".join([f"🏆 نفر {i+1}: {p}" for i, p in enumerate(data["prizes"])])
        + f"\n\n📅 شروع: {data['start_time']}\n⏳ پایان: {data['end_time']}"
        + f"\n\n🔗 برای ثبت‌نام در چالش کلیک کنید:\n{reg_link}"
        + f"\n\n📢 کانال: {data.get('channel_link','')}"
        + f"\n👤 مالک: {owner_id}"
    )
    sent = await context.bot.send_message(chat_id=data["channel_id"], text=banner)
    try:
        await context.bot.pin_chat_message(chat_id=data["channel_id"], message_id=sent.message_id)
    except Exception:
        pass

    await query.message.reply_text(t(lang, "challenge_published", link=reg_link))
    return ConversationHandler.END

owner_conversation_handler = ConversationHandler(
    entry_points=[],
    states={
        CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
        WINNERS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_winners_count)],
        PRIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prize)],
        START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_time)],
        END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_time)],
        STARS_TOGGLE: [__import__("telegram.ext", fromlist=["CallbackQueryHandler"]).CallbackQueryHandler(receive_stars_toggle, pattern="^stars_")],
        STARS_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_stars_rate)],
        PREVIEW: [__import__("telegram.ext", fromlist=["CallbackQueryHandler"]).CallbackQueryHandler(confirm_or_cancel, pattern="^preview_")],
    },
    fallbacks=[],
    per_message=False
)
