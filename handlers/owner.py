from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import create_challenge

async def start_owner_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["new_challenge"] = {}
    context.user_data["state"] = "await_channel"
    await update.callback_query.message.reply_text(t(lang, "ask_channel"))

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    channel = update.message.text.strip()
    try:
        chat = await context.bot.get_chat(channel)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text(t(lang, "bot_not_admin"))
            return
    except Exception:
        await update.message.reply_text(t(lang, "bot_not_admin"))
        return

    context.user_data["new_challenge"]["channel_id"] = chat.id
    context.user_data["new_challenge"]["channel_username"] = chat.username
    context.user_data["new_challenge"]["channel_link"] = f"https://t.me/{chat.username}" if chat.username else ""
    context.user_data["state"] = "await_winners_count"
    await update.message.reply_text(t(lang, "ask_winners_count"))

async def receive_winners_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        count = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(t(lang, "ask_winners_count"))
        return
    context.user_data["new_challenge"]["winners_count"] = count
    context.user_data["new_challenge"]["prizes"] = []
    context.user_data["prize_rank"] = 1
    context.user_data["state"] = "await_prize"
    await update.message.reply_text(t(lang, "ask_prize", rank=1))

async def receive_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    prizes = context.user_data["new_challenge"]["prizes"]
    prizes.append(update.message.text.strip())
    rank = context.user_data["prize_rank"] + 1
    total = context.user_data["new_challenge"]["winners_count"]
    if rank <= total:
        context.user_data["prize_rank"] = rank
        await update.message.reply_text(t(lang, "ask_prize", rank=rank))
        return
    context.user_data["state"] = "await_start_time"
    await update.message.reply_text(t(lang, "ask_start_time"))

def parse_dt(text):
    from datetime import datetime
    return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")

async def receive_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        context.user_data["new_challenge"]["start_time"] = parse_dt(update.message.text)
    except ValueError:
        await update.message.reply_text(t(lang, "ask_start_time"))
        return
    context.user_data["state"] = "await_end_time"
    await update.message.reply_text(t(lang, "ask_end_time"))

async def receive_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        context.user_data["new_challenge"]["end_time"] = parse_dt(update.message.text)
    except ValueError:
        await update.message.reply_text(t(lang, "ask_end_time"))
        return
    context.user_data["state"] = None
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "btn_yes"), callback_data="stars_yes"),
        InlineKeyboardButton(t(lang, "btn_no"), callback_data="stars_no")
    ]])
    await update.message.reply_text(t(lang, "ask_stars"), reply_markup=kb)

async def stars_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "stars_yes":
        context.user_data["new_challenge"]["stars_enabled"] = True
        context.user_data["state"] = "await_stars_rate"
        await query.message.reply_text(t(lang, "ask_stars_rate"))
        return
    context.user_data["new_challenge"]["stars_enabled"] = False
    context.user_data["new_challenge"]["stars_rate"] = 0
    await show_preview(update, context)

async def receive_stars_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        rate = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(t(lang, "ask_stars_rate"))
        return
    context.user_data["new_challenge"]["stars_rate"] = rate
    context.user_data["state"] = None
    await show_preview(update, context)

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

async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "preview_cancel":
        context.user_data["new_challenge"] = {}
        context.user_data["state"] = None
        await query.message.reply_text("لغو شد. دوباره از منو شروع کن.")
        return

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

    context.user_data["new_challenge"] = {}
    context.user_data["state"] = None
    await query.message.reply_text(t(lang, "challenge_published", link=reg_link))
