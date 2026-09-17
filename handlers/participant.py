from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import add_participant, participants, get_challenge, is_blocked, create_report
from bson import ObjectId


def registration_start_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎯 شروع ثبت‌نام", callback_data="register_start")]])


async def enter_participant_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id) if challenge_id else None
    if not challenge or not challenge.get("active"):
        await update.effective_message.reply_text(t(lang, "challenge_missing"))
        return
    context.user_data["state"] = "await_name"
    await update.effective_message.reply_text(t(lang, "ask_name"))


async def receive_name(update, context):
    context.user_data["p_name"] = update.message.text.strip()[:80]
    context.user_data["state"] = "await_age"
    await update.message.reply_text(t(context.user_data.get("lang", "fa"), "ask_age"))


async def receive_age(update, context):
    lang = context.user_data.get("lang", "fa")
    raw = update.message.text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    try:
        age = int(raw)
        if not 5 <= age <= 100: raise ValueError
    except ValueError:
        await update.message.reply_text(t(lang, "invalid_number"))
        return
    context.user_data["p_age"] = age
    context.user_data["state"] = "await_city"
    await update.message.reply_text(t(lang, "ask_city"))


async def receive_city(update, context):
    context.user_data["p_city"] = update.message.text.strip()[:80]
    context.user_data["state"] = "await_photo"
    await update.message.reply_text(t(context.user_data.get("lang", "fa"), "ask_photo"))


async def receive_photo(update, context):
    lang = context.user_data.get("lang", "fa")
    if not update.message.photo:
        await update.message.reply_text(t(lang, "ask_photo")); return
    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        await update.message.reply_text(t(lang, "challenge_missing")); return
    user = update.effective_user
    if is_blocked(user.id): return
    number, created = add_participant(challenge_id, user.id, context.user_data["p_name"], context.user_data["p_age"], context.user_data["p_city"], update.message.photo[-1].file_id, challenge["channel_id"])
    if not created:
        await update.message.reply_text(t(lang, "duplicate", number=number)); return
    reg_link = context.user_data.get("registration_link") or f"https://t.me/{context.bot.username}?start=CH{challenge_id}"
    caption = build_participant_banner(challenge, number, context.user_data["p_name"], context.user_data["p_age"], context.user_data["p_city"], reg_link)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "like_button", count=0), callback_data=f"like_{challenge_id}_{number}")]])
    sent = await context.bot.send_photo(chat_id=challenge["channel_id"], photo=update.message.photo[-1].file_id, caption=caption, reply_markup=kb)
    participants.update_one({"challenge_id": challenge_id, "number": number}, {"$set": {"post_message_id": sent.message_id}})
    await update.message.reply_text(t(lang, "registered", number=number, city=context.user_data["p_city"]), reply_markup=main_menu_keyboard(lang))
    context.user_data["last_challenge_id"] = challenge_id
    context.user_data["state"] = None


def build_participant_banner(challenge, number, name, age, city, reg_link):
    prizes = challenge.get("prizes", [])
    prize_text = "\n".join([f"🏆 نفر {i+1}: {p}" for i, p in enumerate(prizes)]) or "🏆 جوایز طبق اعلام برگزارکننده"
    rules = challenge.get("rules") or "📜 قوانین: لطفاً از لایک‌های فیک و غیرواقعی خودداری کنید. فعالیت غیرطبیعی ممکن است باعث حذف لایک‌ها و حذف شرکت‌کننده از چالش شود."
    channel_link = challenge.get("channel_link") or ""
    owner = challenge.get("owner_username") or "نامشخص"
    return (f"🌟 چالش لایکی | شرکت‌کننده شماره {number}\n\n"
            f"👤 نام: {name}\n🎂 سن: {age}\n📍 ولایت/شهر: {city}\n\n"
            f"🏆 برنده‌ها و جوایز\n{prize_text}\n\n"
            f"📜 قوانین چالش\n{rules}\n\n"
            f"📢 کانال: {channel_link}\n👑 مالک: {owner}\n🎯 ثبت‌نام چالش: {reg_link}")


async def my_stats(update, context):
    from handlers.start import main_menu_keyboard
    lang = context.user_data.get("lang", "fa")
    docs = list(participants.find({"user_id": update.effective_user.id}).sort("registered_at", -1))
    if not docs:
        await update.effective_message.reply_text(t(lang, "stats_empty"), reply_markup=main_menu_keyboard(lang)); return
    total_likes = sum(int(x.get("likes", 0)) for x in docs)
    total_stars = sum(int(x.get("stars_received", 0)) for x in docs)
    details=[]; total_score=0
    for p in docs[:10]:
        ch=get_challenge(p["challenge_id"]); rate=(ch or {}).get("stars_rate", 0); score=p.get("likes",0)+p.get("stars_received",0)*rate; total_score+=score
        details.append(t(lang,"challenge_detail",title=(ch or {}).get("title","-"),number=p.get("number"),likes=p.get("likes",0),stars=p.get("stars_received",0),score=score))
    await update.effective_message.reply_text(t(lang,"my_stats_text",challenges=len(docs),likes=total_likes,stars=total_stars,score=total_score,details="\n".join(details)),reply_markup=main_menu_keyboard(lang))


async def report_panel(update, context):
    lang=context.user_data.get("lang","fa")
    docs=list(participants.find({"user_id":update.effective_user.id}).sort("registered_at",-1).limit(10))
    if not docs:
        await update.effective_message.reply_text(t(lang,"report_none")); return
    buttons=[]
    for p in docs:
        ch=get_challenge(p["challenge_id"])
        if ch: buttons.append([InlineKeyboardButton(f"🎯 {ch.get('title','چالش')} #{p.get('number')}",callback_data=f"reportch_{p['challenge_id']}")])
    await update.effective_message.reply_text(t(lang,"report_choose"),reply_markup=InlineKeyboardMarkup(buttons))


async def report_challenge_callback(update, context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa"); cid=q.data.split("_",1)[1]
    context.user_data["report_challenge_id"]=cid
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"report_prize"),callback_data="reason_prize"),InlineKeyboardButton(t(lang,"report_problem"),callback_data="reason_problem")],[InlineKeyboardButton(t(lang,"report_changed"),callback_data="reason_changed"),InlineKeyboardButton(t(lang,"report_suspicious"),callback_data="reason_suspicious")],[InlineKeyboardButton(t(lang,"report_other"),callback_data="reason_other")]])
    await q.message.reply_text(t(lang,"report_choose"),reply_markup=kb)

async def report_reason_callback(update, context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa")
    reason=q.data.split("_",1)[1]; context.user_data["report_reason"]=reason; context.user_data["state"]="await_report_text"
    await q.message.reply_text(t(lang,"ask_report_text"))

async def receive_report_text(update, context):
    lang=context.user_data.get("lang","fa"); cid=context.user_data.get("report_challenge_id"); reason=context.user_data.get("report_reason"); text=update.message.text.strip()[:1000]
    rid=create_report(update.effective_user.id,cid,reason,text)
    context.user_data["state"]=None
    from config import ADMIN_ID
    ch=get_challenge(cid)
    try:
        await context.bot.send_message(ADMIN_ID, f"🚨 گزارش جدید #{rid}\n👤 کاربر: {update.effective_user.id}\n🎯 چالش: {(ch or {}).get('title','-')}\n📌 دلیل: {reason}\n📝 {text}")
    except Exception:
        pass
    await update.message.reply_text(t(lang,"report_received"),reply_markup=__import__('handlers.start',fromlist=['main_menu_keyboard']).main_menu_keyboard(lang))
