from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bson import ObjectId
from lang import t
from database import challenges, add_participant, participant_for_user, set_participant_post, set_joined_status, user_active_participations, save_report, get_challenge


def participant_banner(challenge, participant):
    prizes = "\n".join(f"{medal} نفر {i}: {prize}" for i, (medal, prize) in enumerate(zip(["🥇", "🥈", "🥉"] + ["🏅"] * 17, challenge.get("prizes", [])), 1))
    rules = challenge.get("rules") or "پیش‌فرض"
    if rules.lower() in {"default", "پیش‌فرض", "پیش فرض"}:
        rules = "🚫 از لایک‌های فیک و غیرواقعی استفاده نکنید؛ فعالیت‌های مشکوک بررسی می‌شود و ممکن است باعث کسر لایک یا حذف از چالش شود."
    channel = challenge.get("channel_link") or (f"https://t.me/{challenge.get('channel_username')}" if challenge.get("channel_username") else "-")
    owner = challenge.get("owner_username") or "-"
    reg = challenge.get("registration_link") or "-"
    return (
        "🌟 شرکت‌کننده چالش لایکی 🌟\n\n"
        f"🎯 شماره شرکت‌کننده: {participant['number']}\n\n"
        f"👤 نام: {participant['name']}\n"
        f"🎂 سن: {participant['age']} سال\n"
        f"📍 ولایت / شهر: {participant['city']}\n\n"
        "━━━━━━━━━━━━━━\n"
        "🏆 جوایز چالش\n"
        f"{prizes or '🏆 هنوز جایزه‌ای ثبت نشده است.'}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📜 قوانین چالش\n"
        f"{rules}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🎯 ثبت‌نام: {reg}\n\n"
        f"📢 کانال: {channel}\n"
        f"👑 برگزارکننده: {owner}\n\n"
        f"❤️ موفق باشی {participant['name']}!\n"
        "🔥 تا پایان چالش برای جمع‌کردن لایک بیشتر تلاش کن!"
    )


def like_keyboard(challenge_id, participant_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("❤️ لایک", callback_data=f"like_{challenge_id}_{participant_id}")]])


async def enter_participant_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        target = update.message or update.callback_query.message
        await target.reply_text(t(lang, "challenge_closed"))
        return
    existing = participant_for_user(challenge_id, update.effective_user.id)
    if existing:
        target = update.message or update.callback_query.message
        await target.reply_text(t(lang, "already_registered", number=existing["number"]))
        return
    context.user_data["state"] = "await_name"
    target = update.message or update.callback_query.message
    await target.reply_text(t(lang, "enter_welcome", title=challenge.get("title", "چالش لایکی"), winners=len(challenge.get("prizes", []))))
    await target.reply_text(t(lang, "ask_name"))


async def start_participation_from_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, challenge_id):
    context.user_data["pending_challenge_id"] = str(challenge_id)
    await enter_participant_flow(update, context)


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    name = (update.message.text or "").strip()
    if not name or len(name) > 60:
        await update.message.reply_text(t(lang, "ask_name"))
        return
    context.user_data["p_name"] = name
    context.user_data["state"] = "await_age"
    await update.message.reply_text(t(lang, "ask_age"))


async def receive_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    try:
        age = int((update.message.text or "").strip())
    except ValueError:
        age = 0
    if not 5 <= age <= 100:
        await update.message.reply_text(t(lang, "bad_age"))
        return
    context.user_data["p_age"] = age
    context.user_data["state"] = "await_city"
    await update.message.reply_text(t(lang, "ask_city"))


async def receive_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    city = (update.message.text or "").strip()
    if not city or len(city) > 80:
        await update.message.reply_text(t(lang, "ask_city"))
        return
    context.user_data["p_city"] = city
    context.user_data["state"] = "await_photo"
    await update.message.reply_text(t(lang, "ask_photo"))


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    if not update.message or not update.message.photo:
        await update.message.reply_text(t(lang, "ask_photo"))
        return
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        await update.message.reply_text(t(lang, "challenge_closed"))
        return
    user = update.effective_user
    existing = participant_for_user(challenge_id, user.id)
    if existing:
        await update.message.reply_text(t(lang, "already_registered", number=existing["number"]))
        return

    joined = False
    try:
        member = await context.bot.get_chat_member(challenge["channel_id"], user.id)
        joined = member.status in ("member", "administrator", "creator")
    except Exception:
        joined = False

    photo_file_id = update.message.photo[-1].file_id
    participant, created = add_participant(
        challenge_id, user.id, context.user_data["p_name"], context.user_data["p_age"],
        context.user_data["p_city"], photo_file_id, challenge["channel_id"], joined,
    )
    if not created:
        await update.message.reply_text(t(lang, "already_registered", number=participant["number"]))
        return

    sent = await context.bot.send_photo(
        chat_id=challenge["channel_id"],
        photo=photo_file_id,
        caption=participant_banner(challenge, participant),
        reply_markup=like_keyboard(challenge_id, str(participant["_id"])),
    )
    set_participant_post(challenge_id, user.id, sent.message_id)
    set_joined_status(challenge_id, user.id, joined)

    await update.message.reply_text(t(lang, "registered", number=participant["number"], city=participant["city"], name=participant["name"]))
    context.user_data.pop("pending_challenge_id", None)
    context.user_data["state"] = None
    from handlers.start import send_main_menu
    await send_main_menu(update.message, context, lang, user.id)


def report_keyboard(challenge_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 جایزه پرداخت نشده", callback_data=f"report_{challenge_id}_prize")],
        [InlineKeyboardButton("⚠️ مشکل در اجرای چالش", callback_data=f"report_{challenge_id}_problem")],
        [InlineKeyboardButton("✏️ اطلاعات تغییر کرده", callback_data=f"report_{challenge_id}_changed")],
        [InlineKeyboardButton("🔍 رفتار مشکوک", callback_data=f"report_{challenge_id}_suspicious")],
        [InlineKeyboardButton("📝 مورد دیگر", callback_data=f"report_{challenge_id}_other")],
    ])


async def open_report_flow(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    context.user_data["report_challenge_id"] = str(challenge_id)
    await query.message.reply_text(t(lang, "report_menu"), reply_markup=report_keyboard(challenge_id))

async def receive_report_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    challenge_id = context.user_data.get("report_challenge_id")
    reason = context.user_data.get("report_reason", "other")
    details = (update.message.text or "").strip()
    if not challenge_id or not details:
        await update.message.reply_text(t(lang, "report_text"))
        return
    challenge = get_challenge(challenge_id)
    if not challenge:
        await update.message.reply_text(t(lang, "challenge_closed")); return
    report_id = save_report(challenge_id, update.effective_user.id, challenge.get("owner_id"), reason, details)
    from config import ADMIN_ID
    reporter = f"@{update.effective_user.username}" if update.effective_user.username else "بدون username"
    admin_text = (
        "🚨 گزارش جدید چالش\n\n"
        f"🎯 چالش: {challenge.get('title','-')}\n"
        f"📢 کانال: {challenge.get('channel_link') or challenge.get('channel_username') or '-'}\n"
        f"👤 گزارش‌دهنده: {reporter}\n"
    )
    admin_text += f"\n📝 دلیل: {reason}\n📄 توضیح: {details}\n🆔 Report: {report_id}"
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    except Exception:
        pass
    context.user_data.pop("report_challenge_id", None)
    context.user_data.pop("report_reason", None)
    context.user_data["state"] = None
    await update.message.reply_text(t(lang, "report_saved"))
