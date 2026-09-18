from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import register_user_start, set_user_language, get_user_language, owner_active_challenges, active_challenges, increment_deep_link_start, get_challenge, user_active_participations
from handlers.participant import report_keyboard, start_participation_from_challenge


def language_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("fa", "btn_fa"), callback_data="lang_fa"), InlineKeyboardButton(t("en", "btn_en"), callback_data="lang_en")]])


def main_menu_keyboard(lang, has_owner_challenges=False, admin=False):
    rows = [
        [InlineKeyboardButton(t(lang, "btn_active"), callback_data="menu_active"), InlineKeyboardButton(t(lang, "btn_new"), callback_data="menu_new")],
        [InlineKeyboardButton(t(lang, "btn_stats"), callback_data="menu_stats"), InlineKeyboardButton(t(lang, "btn_results"), callback_data="menu_results")],
        [InlineKeyboardButton(t(lang, "btn_settings"), callback_data="menu_settings"), InlineKeyboardButton(t(lang, "btn_about"), callback_data="about")],
    ]
    if has_owner_challenges:
        rows.insert(2, [InlineKeyboardButton(t(lang, "btn_owner_manage"), callback_data="menu_owner")])
    if admin:
        rows.insert(0, [InlineKeyboardButton("🛡️ مدیریت مرکزی", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


async def send_main_menu(target, context, lang, user_id):
    from config import ADMIN_ID
    has_owner = bool(owner_active_challenges(user_id, 1))
    await target.reply_text(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang, has_owner, user_id == ADMIN_ID))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    saved_lang = get_user_language(user.id)
    register_user_start(user.id, user.username or "", saved_lang)
    if context.args:
        payload = context.args[0]
        if payload.startswith("CH"):
            challenge_id = payload[2:]
            challenge = get_challenge(challenge_id)
            if challenge and challenge.get("active"):
                context.user_data.clear()
                context.user_data["lang"] = saved_lang
                context.user_data["pending_challenge_id"] = challenge_id
                increment_deep_link_start(challenge_id)
                await start_participation_from_challenge(update, context, challenge_id)
                return
    context.user_data["lang"] = saved_lang
    await update.message.reply_text(t(saved_lang, "welcome"))
    await send_main_menu(update.message, context, saved_lang, user.id)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_", 1)[1]
    context.user_data["lang"] = lang
    set_user_language(query.from_user.id, lang)
    await query.message.reply_text(t(lang, "language_saved"))
    await send_main_menu(query.message, context, lang, query.from_user.id)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get("lang", "fa")

    if data == "menu_new":
        from handlers.owner import start_owner_flow
        await start_owner_flow(update, context); return
    if data == "menu_active":
        items = active_challenges()
        if not items:
            await query.message.reply_text(t(lang, "active_empty")); return
        rows = []
        for c in items:
            rows.append([InlineKeyboardButton(f"🎯 {c.get('title','چالش')} | @{c.get('channel_username') or 'private'}", callback_data=f"challenge_view_{c['_id']}")])
        await query.message.reply_text(t(lang, "active_title"), reply_markup=InlineKeyboardMarkup(rows)); return
    if data == "menu_stats":
        items = user_active_participations(query.from_user.id)
        if not items:
            await query.message.reply_text(t(lang, "stats_none")); return
        if len(items) == 1:
            await send_user_stats(query.message, context, items[0][0], items[0][1]); return
        rows = []
        for c, p in items:
            channel = c.get("channel_username") or "private"
            rows.append([InlineKeyboardButton(f"📢 @{channel} — {c.get('title','چالش')}", callback_data=f"stats_{c['_id']}")])
        await query.message.reply_text(t(lang, "stats_pick"), reply_markup=InlineKeyboardMarkup(rows)); return
    if data == "menu_owner":
        from handlers.owner import show_owner_menu
        await show_owner_menu(query, context); return
    if data == "menu_settings":
        await query.message.reply_text(t(lang, "choose_language"), reply_markup=language_keyboard()); return
    if data == "menu_results":
        await query.message.reply_text(t(lang, "results")); return
    if data == "menu_back":
        await send_main_menu(query.message, context, lang, query.from_user.id); return
    if data == "admin_panel":
        from handlers.admin import admin_panel_callback
        await admin_panel_callback(update, context); return
    if data == "admin_stats":
        from handlers.admin import admin_stats_callback
        await admin_stats_callback(query, context); return
    if data == "admin_challenges":
        from handlers.admin import admin_challenges_callback
        await admin_challenges_callback(query, context); return
    if data == "admin_reports":
        from handlers.admin import show_open_reports
        await show_open_reports(query, context); return
    if data.startswith("admin_report_"):
        from handlers.admin import admin_report_detail
        await admin_report_detail(query, context, data.split("_", 2)[2]); return
    if data.startswith("admin_close_report_"):
        from handlers.admin import close_report_callback
        await close_report_callback(query, context, data.split("_", 3)[3]); return
    if data.startswith("challenge_view_"):
        challenge_id = data.split("_", 2)[2]
        c = get_challenge(challenge_id)
        if not c or not c.get("active"):
            await query.message.reply_text(t(lang, "challenge_closed")); return
        from handlers.owner import format_local_day
        day, tm = format_local_day(c["start_time"], c.get("timezone", "Asia/Kabul"))
        text = f"🌟 {c.get('title','چالش لایکی')}\n\n🏆 {len(c.get('prizes',[]))} جایزه\n📅 شروع: {day} ساعت {tm}\n⏳ مدت: {c.get('duration_hours',24):g} ساعت\n📢 {c.get('channel_link') or '-'}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "join_challenge"), callback_data=f"challenge_join_{challenge_id}")]])
        await query.message.reply_text(text, reply_markup=kb); return
    if data.startswith("challenge_join_"):
        challenge_id = data.split("_", 2)[2]
        context.user_data["pending_challenge_id"] = challenge_id
        await start_participation_from_challenge(update, context, challenge_id); return
    if data.startswith("stats_"):
        challenge_id = data.split("_", 1)[1]
        items = user_active_participations(query.from_user.id)
        found = next(((c,p) for c,p in items if str(c["_id"]) == challenge_id), None)
        if not found:
            await query.message.reply_text(t(lang, "stats_none")); return
        await send_user_stats(query.message, context, found[0], found[1]); return
    if data.startswith("owner_ch_"):
        from handlers.owner import owner_challenge_detail
        await owner_challenge_detail(query, context, data.split("_", 2)[2]); return
    if data.startswith("owner_stats_"):
        from handlers.owner import owner_stats
        await owner_stats(query, context, data.split("_", 2)[2]); return
    if data.startswith("owner_people_"):
        from handlers.owner import owner_people
        await owner_people(query, context, data.split("_", 2)[2]); return
    if data.startswith("owner_board_"):
        from handlers.owner import owner_board
        await owner_board(query, context, data.split("_", 2)[2]); return
    if data.startswith("report_open_"):
        context.user_data["report_challenge_id"] = data.split("_", 2)[2]
        context.user_data["state"] = "await_report_text"
        await query.message.reply_text(t(lang, "report_text")); return
    if data.startswith("report_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            challenge_id, reason = parts[1], parts[2]
            context.user_data["report_challenge_id"] = challenge_id
            context.user_data["report_reason"] = reason
            context.user_data["state"] = "await_report_text"
            await query.message.reply_text(t(lang, "report_text")); return
    if data == "report_open":
        from handlers.admin import show_open_reports
        await show_open_reports(query, context); return


async def send_user_stats(target, context, challenge, participant):
    from handlers.owner import remaining_text
    lang = context.user_data.get("lang", "fa")
    rate = int(challenge.get("stars_rate", 0)) if challenge.get("stars_enabled") else 0
    score = int(participant.get("likes",0)) + int(participant.get("stars_received",0))*rate
    await target.reply_text(t(lang, "stats_header", title=challenge.get("title","-"), channel=challenge.get("channel_link") or challenge.get("channel_username") or "-", number=participant.get("number"), likes=participant.get("likes",0), stars=participant.get("stars_received",0), score=score, remaining=remaining_text(challenge["end_time"])), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚨 گزارش چالش", callback_data=f"report_open_{challenge['_id']}")]]))
