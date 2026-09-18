from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import re
import jdatetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import create_challenge, set_registration_link, owner_active_challenges, challenge_stats, participants, challenges, audit, get_challenge, get_leaderboard

TZS = {"af": "Asia/Kabul", "ir": "Asia/Tehran", "de": "Europe/Berlin"}
WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def timezone_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "tz_af"), callback_data="tz_af"), InlineKeyboardButton(t(lang, "tz_ir"), callback_data="tz_ir")],
        [InlineKeyboardButton(t(lang, "tz_de"), callback_data="tz_de")],
    ])


def owner_day_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "today"), callback_data="owner_day_today"), InlineKeyboardButton(t(lang, "tomorrow"), callback_data="owner_day_tomorrow")],
        [InlineKeyboardButton(t(lang, "day_after"), callback_data="owner_day_after"), InlineKeyboardButton(t(lang, "choose_date"), callback_data="owner_day_custom")],
    ])


def yes_no_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "yes"), callback_data="stars_yes"), InlineKeyboardButton(t(lang, "no"), callback_data="stars_no")]])


def preview_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_confirm"), callback_data="preview_confirm"), InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="preview_cancel")]])


def parse_time(text):
    raw = str(text).strip().lower().replace("٫", ":")
    replacements = {"صبح": " am", "قبل‌ازظهر": " am", "قبل از ظهر": " am", "ظهر": " pm", "عصر": " pm", "شب": " pm", "ب.ظ": " pm", "ق.ظ": " am"}
    for a, b in replacements.items():
        raw = raw.replace(a, b)
    raw = re.sub(r"\s+", " ", raw)
    m = re.fullmatch(r"(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?", raw)
    if not m:
        raise ValueError
    h, minute = int(m.group(1)), int(m.group(2) or 0)
    ap = m.group(3)
    if minute > 59:
        raise ValueError
    if ap:
        if not 1 <= h <= 12:
            raise ValueError
        if ap == "pm" and h != 12: h += 12
        if ap == "am" and h == 12: h = 0
    elif h > 23:
        raise ValueError
    return h, minute


def parse_date(text):
    raw = str(text).strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) != 3:
        raise ValueError
    y, m, d = map(int, parts)
    if y < 1700:
        return jdatetime.date(y, m, d).togregorian()
    return date(y, m, d)


def local_dt_for_date(d, h, minute, tz_name):
    return datetime(d.year, d.month, d.day, h, minute, tzinfo=ZoneInfo(tz_name))


def format_local_day(dt_utc, tz_name):
    if dt_utc.tzinfo is None:
        aware = dt_utc.replace(tzinfo=timezone.utc)
    else:
        aware = dt_utc.astimezone(timezone.utc)
    local = aware.astimezone(ZoneInfo(tz_name))
    return WEEKDAYS_FA[local.weekday()], local.strftime("%H:%M")


def remaining_text(end_time):
    end = end_time.replace(tzinfo=timezone.utc) if end_time.tzinfo is None else end_time.astimezone(timezone.utc)
    seconds = max(0, int((end - datetime.now(timezone.utc)).total_seconds()))
    hours, rem = divmod(seconds, 3600)
    return f"{hours} ساعت و {rem // 60} دقیقه"


def default_rules(rules):
    if not rules or str(rules).strip().lower() in {"default", "پیش‌فرض", "پیش فرض"}:
        return "🚫 از لایک‌های فیک و غیرواقعی استفاده نکنید؛ فعالیت‌های مشکوک بررسی می‌شود و ممکن است باعث کسر لایک یا حذف از چالش شود."
    return rules


def prize_lines(prizes):
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 17
    return "\n".join(f"{medals[i-1]} نفر {i}: {p}" for i, p in enumerate(prizes, 1))


def challenge_banner(data, reg_link):
    day, tm = format_local_day(data["start_time"], data["timezone"])
    stars = f"⭐️ هر 1 Star = {data.get('stars_rate', 0)} Like" if data.get("stars_enabled") else "⭐️ Stars در این چالش فعال نیست"
    return (
        "🌟 چالش لایکی داریم؛ شانست رو آزمایش کن! 🌟\n\n"
        f"🎯 {data.get('title', 'چالش لایکی')}\n"
        "❤️ رقابت کن، لایک جمع کن و برای جایزه تلاش کن!\n\n"
        "━━━━━━━━━━━━━━\n"
        "🏆 جوایز\n"
        f"{prize_lines(data.get('prizes', []))}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"📅 شروع: {day} — {tm}\n"
        f"⏳ مدت: {data.get('duration_hours', 24):g} ساعت\n"
        f"{stars}\n\n"
        "━━━━━━━━━━━━━━\n"
        "📜 قوانین\n"
        f"{default_rules(data.get('rules'))}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🎯 ثبت‌نام: {reg_link}\n\n"
        f"📢 کانال: {data.get('channel_link') or '-'}\n"
        f"👑 برگزارکننده: {data.get('owner_username') or '-'}\n\n"
        "🔥 چالش لایکی ما فرق داره!\n"
        "🚀 منتظر چالش‌های بعدی باشید."
    )


async def start_owner_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["new_challenge"] = {}
    context.user_data["state"] = "await_title"
    await update.callback_query.message.reply_text(t(lang, "ask_title"))


async def receive_title(update, context):
    lang = context.user_data.get("lang", "fa")
    title = (update.message.text or "").strip()
    if not title or len(title) > 80:
        await update.message.reply_text(t(lang, "ask_title")); return
    context.user_data["new_challenge"]["title"] = title
    context.user_data["state"] = "await_channel"
    await update.message.reply_text(t(lang, "ask_channel"))


def extract_public_channel_username(raw):
    value = raw.strip()
    m = re.fullmatch(r"https?://t\.me/([A-Za-z0-9_]{5,})/?", value)
    if not m:
        return None
    return m.group(1)


async def receive_channel(update, context):
    lang = context.user_data.get("lang", "fa")
    raw = (update.message.text or "").strip()
    username = extract_public_channel_username(raw)
    if not username:
        await update.message.reply_text(t(lang, "bad_channel")); return
    try:
        chat = await context.bot.get_chat("@" + username)
        if chat.type != "channel":
            raise RuntimeError("not channel")
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if member.status not in ("administrator", "creator"):
            raise RuntimeError("not admin")
    except Exception:
        await update.message.reply_text(t(lang, "bad_channel")); return
    context.user_data["new_challenge"].update({"channel_id": chat.id, "channel_username": username, "channel_link": f"https://t.me/{username}"})
    context.user_data["state"] = "await_owner_username"
    await update.message.reply_text(t(lang, "ask_owner_username"))


async def receive_owner_username(update, context):
    lang = context.user_data.get("lang", "fa")
    username = (update.message.text or "").strip()
    if username and not username.startswith("@"):
        username = "@" + username
    if not re.fullmatch(r"@[A-Za-z0-9_]{3,32}", username):
        await update.message.reply_text(t(lang, "bad_username")); return
    context.user_data["new_challenge"]["owner_username"] = username
    context.user_data["state"] = "await_timezone_first"
    await update.message.reply_text(t(lang, "ask_timezone"), reply_markup=timezone_keyboard(lang))


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    tz_key = query.data.split("_", 1)[1]
    tz_name = TZS.get(tz_key)
    data = context.user_data.get("new_challenge")
    if not data or not tz_name:
        await query.message.edit_text("❌ این مرحله منقضی شده. دوباره ساخت چالش را شروع کن."); return
    data["timezone"] = tz_name
    if context.user_data.get("state") == "await_timezone_first":
        context.user_data["state"] = "await_day"
        await query.message.edit_text(t(lang, "ask_day"), reply_markup=owner_day_keyboard(lang))
    else:
        await query.message.edit_text(t(lang, "ask_day"), reply_markup=owner_day_keyboard(lang))


async def day_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    data = context.user_data.get("new_challenge")
    if not data or "timezone" not in data:
        await query.message.edit_text("❌ این مرحله منقضی شده. دوباره ساخت چالش را شروع کن."); return
    if query.data == "owner_day_custom":
        context.user_data["state"] = "await_custom_date"
        await query.message.edit_text(t(lang, "ask_date")); return
    offset = {"owner_day_today": 0, "owner_day_tomorrow": 1, "owner_day_after": 2}.get(query.data)
    if offset is None:
        return
    now = datetime.now(ZoneInfo(data["timezone"]))
    data["day_date"] = (now + timedelta(days=offset)).date().isoformat()
    context.user_data["state"] = "await_time"
    await query.message.edit_text(t(lang, "ask_time"))


async def receive_custom_date(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        d = parse_date(update.message.text)
        if d < date.today():
            raise ValueError
        context.user_data["new_challenge"]["day_date"] = d.isoformat()
    except Exception:
        await update.message.reply_text(t(lang, "bad_date")); return
    context.user_data["state"] = "await_time"
    await update.message.reply_text(t(lang, "ask_time"))


async def receive_time(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        h, minute = parse_time(update.message.text)
        data = context.user_data["new_challenge"]
        date_obj = datetime.fromisoformat(data["day_date"]).date()
        local_start = local_dt_for_date(date_obj, h, minute, data["timezone"])
        start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
        if start_utc <= datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=1):
            raise ValueError
    except Exception:
        await update.message.reply_text(t(lang, "bad_time")); return
    data["hour"], data["minute"], data["start_time"] = h, minute, start_utc
    context.user_data["state"] = "await_duration"
    await update.message.reply_text(t(lang, "ask_duration"))


async def receive_duration(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        hours = float((update.message.text or "").strip().replace(",", "."))
        if not 0 < hours <= 720: raise ValueError
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
        count = int((update.message.text or "").strip())
        if not 1 <= count <= 20: raise ValueError
    except Exception:
        await update.message.reply_text(t(lang, "bad_winners")); return
    context.user_data["new_challenge"].update({"winners_count": count, "prizes": []})
    context.user_data["prize_rank"] = 1
    context.user_data["state"] = "await_prize"
    await update.message.reply_text(t(lang, "ask_prize", rank=1))


async def receive_prize(update, context):
    lang = context.user_data.get("lang", "fa")
    value = (update.message.text or "").strip()
    if not value or len(value) > 200:
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
    rules = (update.message.text or "").strip() or "پیش‌فرض"
    context.user_data["new_challenge"]["rules"] = rules
    context.user_data["state"] = None
    await update.message.reply_text(t(lang, "ask_stars"), reply_markup=yes_no_keyboard(lang))


async def stars_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    data = context.user_data.get("new_challenge")
    if not data:
        await query.message.edit_text("❌ ساخت چالش منقضی شده. دوباره شروع کن."); return
    if query.data == "stars_yes":
        data["stars_enabled"] = True
        context.user_data["state"] = "await_stars_rate"
        await query.message.edit_text(t(lang, "ask_rate"))
    else:
        data["stars_enabled"] = False; data["stars_rate"] = 0
        await show_preview(query.message, context)


async def receive_stars_rate(update, context):
    lang = context.user_data.get("lang", "fa")
    try:
        rate = int((update.message.text or "").strip())
        if not 1 <= rate <= 100: raise ValueError
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
    text = (f"🔍 {t(lang,'preview')}\n\n🎯 {data['title']}\n📢 {data['channel_link']}\n👑 {data['owner_username']}\n"
            f"📅 {day} — {tm}\n⏳ {data['duration_hours']:g} ساعت\n🏆 برنده‌ها: {data['winners_count']}\n\n🎁 جوایز:\n{prizes}\n\n📜 قوانین:\n{default_rules(data.get('rules'))}\n\n⭐️ هر Star: {data['stars_rate'] if data.get('stars_enabled') else 0} Like")
    await message.reply_text(text, reply_markup=preview_keyboard(lang))


async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    if query.data == "preview_cancel":
        context.user_data.pop("new_challenge", None); context.user_data["state"] = None
        await query.message.edit_text(t(lang, "cancelled")); return
    data = context.user_data.get("new_challenge")
    if not data:
        await query.message.edit_text(t(lang, "cancelled")); return
    owner_id = query.from_user.id
    data["owner_id"] = owner_id
    try:
        challenge_id = create_challenge(owner_id, data)
        bot_username = context.bot.username or (await context.bot.get_me()).username
        reg_link = f"https://t.me/{bot_username}?start=CH{challenge_id}"
        set_registration_link(challenge_id, reg_link)
        data["registration_link"] = reg_link
        sent = await context.bot.send_message(chat_id=data["channel_id"], text=challenge_banner(data, reg_link), disable_web_page_preview=True)
        challenges.update_one({"_id": __import__('bson').ObjectId(challenge_id)}, {"$set": {"banner_message_id": sent.message_id}})
        try:
            await context.bot.pin_chat_message(chat_id=data["channel_id"], message_id=sent.message_id, disable_notification=True)
        except Exception:
            pass
        audit(owner_id, "challenge_created", challenge_id, details={"channel_id": data["channel_id"]})
        context.user_data.pop("new_challenge", None); context.user_data["state"] = None
        await query.message.edit_text(t(lang, "published", link=reg_link), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 آمار چالش", callback_data=f"owner_stats_{challenge_id}")]]))
    except Exception:
        context.user_data["state"] = None
        await query.message.edit_text("❌ ساخت چالش انجام نشد. مطمئن شو ربات در کانال ادمین است و دوباره تلاش کن.")


async def owner_stats(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    joined = 0
    for p in participants.find({"challenge_id": str(challenge_id)}, {"user_id": 1, "joined_channel": 1}):
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], p["user_id"])
            current = member.status in ("member", "administrator", "creator", "restricted")
            participants.update_one({"_id": p["_id"]}, {"$set": {"joined_channel": current}})
            joined += int(current)
        except Exception:
            joined += int(p.get("joined_channel", False))
    s = challenge_stats(challenge_id)
    text = t(lang, "owner_stats", title=ch.get("title"), channel=ch.get("channel_link") or "-", participants=s["participants"], joined=joined, likes=s["likes"], stars=s["stars"], starts=ch.get("deep_link_starts", 0), remaining=remaining_text(ch["end_time"]))
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 شرکت‌کنندگان", callback_data=f"owner_people_{challenge_id}")], [InlineKeyboardButton("🏆 رتبه فعلی", callback_data=f"owner_board_{challenge_id}")], [InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu_back")]]))


async def owner_people(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    docs = list(participants.find({"challenge_id": str(challenge_id)}).sort("number", 1).limit(100))
    if not docs:
        await query.message.edit_text("👥 هنوز کسی ثبت‌نام نکرده است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data=f"owner_stats_{challenge_id}")]])); return
    lines = ["👥 شرکت‌کنندگان\n"]
    rate = int(ch.get("stars_rate", 0)) if ch.get("stars_enabled") else 0
    for p in docs:
        score = int(p.get("likes", 0)) + int(p.get("stars_received", 0)) * rate
        lines.append(f"{p['number']}. {p['name']} | ❤️ {p.get('likes',0)} | ⭐️ {p.get('stars_received',0)} | 🔥 {score}")
    await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ آمار چالش", callback_data=f"owner_stats_{challenge_id}")]]))


async def owner_board(query, context, challenge_id):
    lang = context.user_data.get("lang", "fa")
    ch = get_challenge(challenge_id)
    if not ch or ch.get("owner_id") != query.from_user.id:
        await query.answer(t(lang, "not_allowed"), show_alert=True); return
    board = get_leaderboard(challenge_id, ch.get("stars_rate", 0))[:20]
    if not board:
        await query.message.edit_text("🏆 هنوز شرکت‌کننده‌ای وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ آمار چالش", callback_data=f"owner_stats_{challenge_id}")]])); return
    lines = ["🏆 رتبه فعلی\n"]
    for i, p in enumerate(board, 1):
        lines.append(f"{i}. {p['name']} — ❤️ {p.get('likes',0)} | ⭐️ {p.get('stars_received',0)} | 🔥 {p['total_score']}")
    await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ آمار چالش", callback_data=f"owner_stats_{challenge_id}")]]))


async def owner_stats_entry(update, context):
    lang = context.user_data.get("lang", "fa")
    items = owner_active_challenges(update.effective_user.id)
    if not items:
        await update.message.reply_text(t(lang, "owner_none")); return
    if len(items) == 1:
        # synthetic callback-free rendering
        class Q:
            from_user = update.effective_user
            message = update.message
            async def answer(self, *args, **kwargs): pass
        await owner_stats(Q(), context, str(items[0]["_id"]))
        return
    rows = [[InlineKeyboardButton(f"🎯 {c.get('title','چالش')}", callback_data=f"owner_stats_{c['_id']}")] for c in items]
    await update.message.reply_text(t(lang, "owner_pick"), reply_markup=InlineKeyboardMarkup(rows))
