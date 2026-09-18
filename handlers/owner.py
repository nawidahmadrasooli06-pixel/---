from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re
import jdatetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import create_challenge, set_registration_link, owner_active_challenges, challenge_stats, participants, challenges, audit, get_challenge, get_leaderboard

TZS = {"af": "Asia/Kabul", "ir": "Asia/Tehran", "de": "Europe/Berlin"}


def owner_day_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "today"), callback_data="owner_day_today"), InlineKeyboardButton(t(lang, "tomorrow"), callback_data="owner_day_tomorrow")],
        [InlineKeyboardButton(t(lang, "day_after"), callback_data="owner_day_after"), InlineKeyboardButton(t(lang, "choose_date"), callback_data="owner_day_custom")],
    ])


def timezone_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "tz_af"), callback_data="tz_af"), InlineKeyboardButton(t(lang, "tz_ir"), callback_data="tz_ir")],
        [InlineKeyboardButton(t(lang, "tz_de"), callback_data="tz_de")],
    ])


def yes_no_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ بله", callback_data="stars_yes"), InlineKeyboardButton("❌ خیر", callback_data="stars_no")]])


def preview_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_confirm"), callback_data="preview_confirm"), InlineKeyboardButton(t(lang, "btn_edit"), callback_data="preview_cancel")]])


def owner_manage_keyboard(lang, items):
    rows = []
    for c in items:
        rows.append([InlineKeyboardButton(f"🎯 {c.get('title','چالش')} — @{c.get('channel_username') or 'private'}", callback_data=f"owner_ch_{c['_id']}")])
    return InlineKeyboardMarkup(rows + [[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]])


def owner_detail_keyboard(lang, challenge_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار چالش", callback_data=f"owner_stats_{challenge_id}")],
        [InlineKeyboardButton("👥 شرکت‌کنندگان", callback_data=f"owner_people_{challenge_id}")],
        [InlineKeyboardButton("🏆 رتبه فعلی", callback_data=f"owner_board_{challenge_id}")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="menu_owner")],
    ])


def parse_time(text):
    raw = text.strip().lower().replace("٫", ":")
    raw = raw.replace("عصر", " pm").replace("شب", " pm").replace("صبح", " am")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?", raw)
    if not m:
        raise ValueError
    h = int(m.group(1)); minute = int(m.group(2) or 0); ap = m.group(3)
    if minute > 59: raise ValueError
    if ap:
        if not 1 <= h <= 12: raise ValueError
        if ap == "pm" and h != 12: h += 12
        if ap == "am" and h == 12: h = 0
    elif h > 23:
        raise ValueError
    return h, minute


def parse_date(text):
    raw = text.strip().replace("-", "/")
    parts = raw.split("/")
    if len(parts) != 3:
        raise ValueError
    y, m, d = map(int, parts)
    if y < 1700:
        return jdatetime.date(y, m, d).togregorian()
    from datetime import date
    return date(y, m, d)


def local_dt_for_date(date_obj, h, minute, tz_name):
    return datetime(date_obj.year, date_obj.month, date_obj.day, h, minute, tzinfo=ZoneInfo(tz_name))


def format_local_day(dt_utc, tz_name):
    local = dt_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz_name))
    weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    return weekdays[local.weekday()], local.strftime("%H:%M")


def remaining_text(end_time):
    end = end_time.replace(tzinfo=timezone.utc)
    delta = end - datetime.now(timezone.utc)
    seconds = max(0, int(delta.total_seconds()))
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    return f"{hours} ساعت و {minutes} دقیقه"


def challenge_banner(data, reg_link):
    prizes = "\n".join(f"{medal} نفر {i}: {p}" for i, (medal, p) in enumerate(zip(["🥇", "🥈", "🥉"] + ["🏅"] * 17, data["prizes"]), 1))
    start_utc = data["start_time"].replace(tzinfo=timezone.utc)
    day, tm = format_local_day(start_utc, data["timezone"])
    rules = data.get("rules") or "پیش‌فرض"
    if rules.lower() in {"default", "پیش‌فرض", "پیش فرض"}:
        rules = "🚫 از لایک‌های فیک و غیرواقعی استفاده نکنید؛ فعالیت‌های مشکوک بررسی می‌شود و ممکن است باعث کسر لایک یا حذف از چالش شود."
    channel = data.get("channel_link") or "-"
    owner = data.get("owner_username") or "-"
    star_line = f"⭐️ هر 1 Star = {data.get('stars_rate', 0)} Like" if data.get("stars_enabled") else "⭐️ Stars در این چالش فعال نیست"
    return (
        "🌟 به چالش لایکی خوش آمدید! 🌟\n\n"
        f"🎯 {data.get('title','چالش لایکی')}\n"
        "❤️ شانست رو آزمایش کن، رقابت کن و برای برنده‌شدن تلاش کن!\n\n"
        "━━━━━━━━━━━━━━\n"
        "🏆 جوایز این چالش\n"
        f"{prizes}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"📅 شروع: {day} ساعت {tm}\n"
        f"⏳ مدت: {data.get('duration_hours', 24):g} ساعت\n"
        f"{star_line}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📜 قوانین چالش\n"
        f"{rules}\n\n"
        "━━━━━━━━━━━━━━\n"
        "🚀 آماده‌ای؟\n"
        "👤 برای شرکت، از لینک زیر وارد ربات شو و ثبت‌نام کن:\n\n"
        f"🎯 ثبت‌نام: {reg_link}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"📢 کانال: {channel}\n"
        f"👑 برگزارکننده: {owner}\n\n"
        "❤️ چالش لایکی ما فرق داره!\n"
        "🔥 لایک جمع کن، رقابت کن و برای جایزه بجنگ!\n"
        "🚀 منتظر چالش‌های بعدی باشید."
    )


async def start_owner_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["new_challenge"] = {}
    context.user_data["state"] = "await_title"
    target = update.callback_query.message
    await target.reply_text(t(lang, "ask_title"))


async def receive_title(update, context):
    lang = context.user_data.get("lang", "fa")
    title = update.message.text.strip()
    if not title or len(title) > 80:
        await update.message.reply_text(t(lang, "ask_title")); return
    context.user_data["new_challenge"]["title"] = title
    context.user_data["state"] = "await_channel"
    await update.message.reply_text(t(lang, "ask_channel"))


async def receive_channel(update, context):
    lang = context.user_data.get("lang", "fa")
    raw = update.message.text.strip()
    try:
        chat = await context.bot.get_chat(raw)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if member.status not in ("administrator", "creator"):
            raise RuntimeError
    except Exception:
        await update.message.reply_text(t(lang, "bot_not_admin")); return
    username = chat.username or ""
    link = f"https://t.me/{username}" if username else raw
    context.user_data["new_challenge"].update({"channel_id": chat.id, "channel_username": username, "channel_link": link})
    context.user_data["state"] = "await_owner_username"
    await update.message.reply_text(t(lang, "ask_owner_username"))


async def receive_owner_username(update, context):
    lang = context.user_data.get("lang", "fa")
    username = update.message.text.strip()
    if username and not username.startswith("@"):
        username = "@" + username
    if len(username) < 2 or len(username) > 40:
        await update.message.reply_text(t(lang, "ask_owner_username")); return
    context.user_data["new_challenge"]["owner_username"] = username
    context.user_data["state"] = "await_timezone_first"
    await update.message.reply_text(t(lang, "ask_timezone"), reply_markup=timezone_keyboard(lang))


async def day_callback(query, context):
    lang = context.user_data.get("lang", "fa")
    now = datetime.now(ZoneInfo(context.user_data["new_challenge"].get("timezone", "Asia/Kabul")))
    choice = query.data
    if choice == "owner_day_custom":
        context.user_data["state"] = "await_custom_date"
        await query.message.reply_text(t(lang, "ask_date")); return
    offset = {"owner_day_today": 0, "owner_day_tomorrow": 1, "owner_day_after": 2}[choice]
    context.user_data["new_challenge"]["day_date"] = (now + timedelta(days=offset)).date().isoformat()
    context.user_data["state"] = "await_time"
    await query.message.reply_text(t(lang, "ask_time"))


async def receive_custom_date(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        d = parse_date(update.message.text)
        context.user_data["new_challenge"]["day_date"] = d.isoformat()
    except Exception:
        await update.message.reply_text(t(lang, "bad_date")); return
    context.user_data["state"] = "await_time"
    await update.message.reply_text(t(lang, "ask_time"))


async def receive_time(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        h, minute = parse_time(update.message.text)
    except Exception:
        await update.message.reply_text(t(lang, "bad_time")); return
    data = context.user_data["new_challenge"]
    data["hour"] = h
    data["minute"] = minute
    tz_name = data.get("timezone", "Asia/Kabul")
    date_obj = datetime.fromisoformat(data["day_date"]).date()
    local_start = local_dt_for_date(date_obj, h, minute, tz_name)
    data["start_time"] = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    context.user_data["state"] = "await_duration"
    await update.message.reply_text(t(lang, "ask_duration"))


async def timezone_callback(query, context):
    lang = context.user_data.get("lang", "fa")
    tz_key = query.data.split("_", 1)[1]
    tz_name = TZS.get(tz_key)
    data = context.user_data["new_challenge"]
    data["timezone"] = tz_name
    if context.user_data.get("state") == "await_timezone_first":
        now = datetime.now(ZoneInfo(tz_name))
        data["today_iso"] = now.date().isoformat()
        context.user_data["state"] = "await_day"
        await query.message.reply_text(t(lang, "ask_day"), reply_markup=owner_day_keyboard(lang))
        return
    # fallback for older state flow
    date_obj = datetime.fromisoformat(data["day_date"]).date()
    local_start = local_dt_for_date(date_obj, data["hour"], data["minute"], tz_name)
    data["start_time"] = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    context.user_data["state"] = "await_duration"
    await query.message.reply_text(t(lang, "ask_duration"))


async def receive_duration(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        hours = float(update.message.text.strip().replace(",", "."))
        if hours <= 0 or hours > 720: raise ValueError
    except Exception:
        await update.message.reply_text(t(lang, "bad_duration")); return
    data = context.user_data["new_challenge"]
    data["duration_hours"] = hours
    data["end_time"] = data["start_time"] + timedelta(hours=hours)
    context.user_data["state"] = "await_winners"
    await update.message.reply_text(t(lang, "ask_winners"))


async def receive_winners(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        count = int(update.message.text.strip())
        if not 1 <= count <= 20: raise ValueError
    except Exception:
        await update.message.reply_text(t(lang, "bad_winners")); return
    context.user_data["new_challenge"]["winners_count"] = count
    context.user_data["new_challenge"]["prizes"] = []
    context.user_data["prize_rank"] = 1
    context.user_data["state"] = "await_prize"
    await update.message.reply_text(t(lang, "ask_prize", rank=1))


async def receive_prize(update, context):
    lang = context.user_data.get("lang", "fa")
    value = update.message.text.strip()
    if not value:
        await update.message.reply_text(t(lang, "ask_prize", rank=context.user_data["prize_rank"])); return
    data = context.user_data["new_challenge"]
    data["prizes"].append(value)
    rank = context.user_data["prize_rank"] + 1
    if rank <= data["winners_count"]:
        context.user_data["prize_rank"] = rank
        await update.message.reply_text(t(lang, "ask_prize", rank=rank)); return
    context.user_data["state"] = "await_rules"
    await update.message.reply_text(t(lang, "ask_rules"))


async def receive_rules(update, context):
    lang = context.user_data.get("lang", "fa")
    context.user_data["new_challenge"]["rules"] = update.message.text.strip() or "پیش‌فرض"
    context.user_data["state"] = None
    await update.message.reply_text(t(lang, "ask_stars"), reply_markup=yes_no_keyboard())


async def stars_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "stars_yes":
        context.user_data["new_challenge"]["stars_enabled"] = True
        context.user_data["state"] = "await_stars_rate"
        await query.message.reply_text(t(lang, "ask_rate"))
    else:
        context.user_data["new_challenge"]["stars_enabled"] = False
        context.user_data["new_challenge"]["stars_rate"] = 0
        await show_preview(query.message, context)


async def receive_stars_rate(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        rate = int(update.message.text.strip())
        if rate <= 0 or rate > 100: raise ValueError
    except Exception:
        await update.message.reply_text(t(lang, "bad_rate")); return
    context.user_data["new_challenge"]["stars_rate"] = rate
    context.user_data["state"] = None
    await show_preview(update.message, context)


async def show_preview(message, context):
    lang = context.user_data.get("lang", "fa")
    data = context.user_data["new_challenge"]
    day, tm = format_local_day(data["start_time"], data["timezone"])
    prizes = "\n".join(f"{i+1}. {p}" for i, p in enumerate(data["prizes"]))
    preview = (
        f"🔍 {t(lang,'preview')}\n\n"
        f"🎯 {data['title']}\n"
        f"📢 {data['channel_link']}\n"
        f"👑 {data['owner_username']}\n"
        f"📅 شروع: {day} ساعت {tm}\n"
        f"⏳ مدت: {data['duration_hours']:g} ساعت\n"
        f"🏆 برنده‌ها: {data['winners_count']}\n\n"
        f"🎁 جوایز:\n{prizes}\n\n"
        f"📜 قوانین: {data['rules']}\n"
        f"⭐️ هر Star: {data['stars_rate'] if data.get('stars_enabled') else 0} Like"
    )
    await message.reply_text(preview, reply_markup=preview_keyboard(lang))


async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.answer()
    if query.data == "preview_cancel":
        context.user_data.pop("new_challenge", None)
        context.user_data["state"] = None
        await query.message.reply_text(t(lang, "cancelled"))
        return
    data = context.user_data.get("new_challenge")
    if not data:
        await query.message.reply_text(t(lang, "cancelled")); return
    owner_id = update.effective_user.id
    data["owner_id"] = owner_id
    challenge_id = create_challenge(owner_id, data)
    reg_link = f"https://t.me/{context.bot.username}?start=CH{challenge_id}"
    set_registration_link(challenge_id, reg_link)
    data["registration_link"] = reg_link
    sent = await context.bot.send_message(chat_id=data["channel_id"], text=challenge_banner(data, reg_link), disable_web_page_preview=True)
    challenges.update_one({"_id": __import__('bson').ObjectId(challenge_id)}, {"$set": {"banner_message_id": sent.message_id}})
    try:
        await context.bot.pin_chat_message(chat_id=data["channel_id"], message_id=sent.message_id, disable_notification=True)
    except Exception:
        pass
    audit(owner_id, "challenge_created", challenge_id, details={"channel_id": data["channel_id"]})
    context.user_data.pop("new_challenge", None)
    context.user_data["state"] = None
    await query.message.reply_text(t(lang, "published", link=reg_link))


async def show_owner_menu(update, context):
    lang = context.user_data.get("lang", "fa")
    items = owner_active_challenges(update.effective_user.id)
    if not items:
        await update.message.reply_text(t(lang, "owner_none")); return
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(t(lang, "owner_pick"), reply_markup=owner_manage_keyboard(lang, items))


async def owner_challenge_detail(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id or not ch.get("active"):
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    await query.message.reply_text(f"🛠 {ch.get('title','چالش')}\n📢 {ch.get('channel_link') or ch.get('channel_username','-')}", reply_markup=owner_detail_keyboard(lang, challenge_id))


async def owner_stats(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    ps = list(participants.find({"challenge_id": str(challenge_id)}))
    joined = 0
    for p in ps:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], p["user_id"])
            current = member.status in ("member", "administrator", "creator")
            participants.update_one({"_id": p["_id"]}, {"$set": {"joined_channel": current}})
            joined += int(current)
        except Exception:
            joined += int(p.get("joined_channel", False))
    s = challenge_stats(challenge_id)
    await query.message.reply_text(t(lang, "owner_stats", title=ch.get("title"), channel=ch.get("channel_link") or ch.get("channel_username") or "-", participants=s["participants"], joined=joined, likes=s["likes"], stars=s["stars"], starts=ch.get("deep_link_starts", 0), remaining=remaining_text(ch["end_time"])))


async def owner_people(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    docs = list(participants.find({"challenge_id": str(challenge_id)}).sort("number", 1).limit(50))
    if not docs:
        await query.message.reply_text("👥 هنوز کسی ثبت‌نام نکرده است."); return
    lines = ["👥 شرکت‌کنندگان:\n"]
    for p in docs:
        score = int(p.get("likes", 0)) + int(p.get("stars_received", 0)) * int(ch.get("stars_rate", 0))
        lines.append(f"{p['number']}. {p['name']} | ❤️ {p.get('likes',0)} | ⭐️ {p.get('stars_received',0)} | 🔥 {score}")
    await query.message.reply_text("\n".join(lines))


async def owner_board(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    board = get_leaderboard(challenge_id, ch.get("stars_rate", 0))[:20]
    if not board:
        await query.message.reply_text("🏆 هنوز شرکت‌کننده‌ای وجود ندارد."); return
    lines = ["🏆 رتبه فعلی:\n"]
    for i, p in enumerate(board, 1):
        lines.append(f"{i}. {p['name']} — 🔥 {p['total_score']}")
    await query.message.reply_text("\n".join(lines))
