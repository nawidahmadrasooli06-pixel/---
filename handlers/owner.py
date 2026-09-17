from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re
import jdatetime
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from config import ADMIN_ID
from database import create_challenge, get_challenge, challenges, challenge_stats, participants, audit, is_blocked, now_utc

TZS={"af":"Asia/Kabul","ir":"Asia/Tehran","de":"Europe/Berlin"}

def tz_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇦🇫 افغانستان",callback_data="tz_af"),InlineKeyboardButton("🇮🇷 ایران",callback_data="tz_ir")],[InlineKeyboardButton("🇩🇪 آلمان",callback_data="tz_de")]])

def yn_keyboard(prefix):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ بله",callback_data=f"{prefix}_yes"),InlineKeyboardButton("❌ خیر",callback_data=f"{prefix}_no")]])

def owner_state(context): return context.user_data.setdefault("new_challenge",{})

async def start_owner_flow(update,context):
    if is_blocked(update.effective_user.id):
        await update.callback_query.message.reply_text(t(context.user_data.get("lang","fa"),"blocked")); return
    context.user_data["new_challenge"]={}; context.user_data["state"]="await_title"
    await update.callback_query.message.reply_text(t(context.user_data.get("lang","fa"),"ask_title"))

async def receive_title(update,context):
    d=owner_state(context); d["title"]=update.message.text.strip()[:200]; context.user_data["state"]="await_channel"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_channel"))

async def receive_channel(update,context):
    lang=context.user_data.get("lang","fa"); raw=update.message.text.strip(); target=raw
    if raw.startswith("https://t.me/") or raw.startswith("http://t.me/"): target="@"+raw.split("t.me/",1)[1].split("/",1)[0].lstrip("@")
    elif not raw.startswith("@"): target="@"+raw.lstrip("@").split("/",1)[0]
    try:
        chat=await context.bot.get_chat(target); member=await context.bot.get_chat_member(chat.id,context.bot.id)
        if member.status not in ("administrator","creator"): raise ValueError()
    except Exception:
        await update.message.reply_text("❌ ربات باید در کانال ادمین باشد و کانال عمومی یا قابل دسترسی باشد. دوباره بفرست."); return
    d=owner_state(context); d.update({"channel_id":chat.id,"channel_username":chat.username or "","channel_link":f"https://t.me/{chat.username}" if chat.username else raw}); context.user_data["state"]="await_owner"; await update.message.reply_text(t(lang,"ask_owner"))

async def receive_owner(update,context):
    u=update.message.text.strip(); u=u if u.startswith("@") else "@"+u; owner_state(context)["owner_username"]=u; context.user_data["state"]="await_timezone"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_tz"),reply_markup=tz_keyboard())

async def timezone_callback(update,context):
    q=update.callback_query; await q.answer(); code=q.data.split("_",1)[1]; owner_state(context)["timezone"]=TZS[code]; context.user_data["state"]="await_start"; await q.message.reply_text(t(context.user_data.get("lang","fa"),"ask_start"))

def parse_datetime(text,tzname):
    text=text.strip().replace("-","/")
    tz=ZoneInfo(tzname)
    parts=re.findall(r"\d+",text)
    if len(parts)<5: raise ValueError
    y,m,d,hh,mm=map(int,parts[:5])
    if y<1700:
        gy=jdatetime.date(y,m,d).togregorian(); y,m,d=gy.year,gy.month,gy.day
    return datetime(y,m,d,hh,mm,tzinfo=tz).astimezone(timezone.utc)

async def receive_start(update,context):
    try: owner_state(context)["start_time"]=parse_datetime(update.message.text,owner_state(context)["timezone"])
    except Exception: await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_start")); return
    context.user_data["state"]="await_duration"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_duration"))

async def receive_duration(update,context):
    try: hours=float(update.message.text.strip().replace(",",".")); assert 0<hours<=8760
    except Exception: await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_duration")); return
    d=owner_state(context); d["duration_hours"]=hours; d["end_time"]=d["start_time"]+timedelta(hours=hours); context.user_data["state"]="await_winners"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_winners"))

async def receive_winners(update,context):
    try: n=int(update.message.text.strip()); assert 1<=n<=50
    except Exception: await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_winners")); return
    d=owner_state(context); d["winners_count"]=n; d["prizes"]=[]; d["prize_rank"]=1; context.user_data["state"]="await_prize"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_prize",rank=1))

async def receive_prize(update,context):
    d=owner_state(context); d["prizes"].append(update.message.text.strip()[:300]); d["prize_rank"]+=1
    if d["prize_rank"]<=d["winners_count"]: await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_prize",rank=d["prize_rank"])); return
    context.user_data["state"]="await_rules"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_rules"))

async def receive_rules(update,context):
    d=owner_state(context); txt=update.message.text.strip(); d["rules"]="" if txt.lower() in ("ندارد","none","нет","لا يوجد") else txt[:2000]; context.user_data["state"]="await_stars"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_stars"),reply_markup=yn_keyboard("stars"))

async def stars_toggle_callback(update,context):
    q=update.callback_query; await q.answer(); d=owner_state(context); yes=q.data.endswith("_yes"); d["stars_enabled"]=yes; d["stars_rate"]=0
    if yes: context.user_data["state"]="await_rate"; await q.message.reply_text(t(context.user_data.get("lang","fa"),"ask_rate"))
    else: context.user_data["state"]="await_confirm"; await show_preview(q.message,context)

async def receive_rate(update,context):
    try: rate=float(update.message.text.strip().replace(",",".")); assert 0<=rate<=1000
    except Exception: await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_rate")); return
    owner_state(context)["stars_rate"]=rate; context.user_data["state"]="await_confirm"; await show_preview(update.message,context)

def preview_text(d):
    prizes="\n".join(f"🏆 {i+1}. {p}" for i,p in enumerate(d["prizes"]))
    start=d["start_time"].astimezone(ZoneInfo(d["timezone"])).strftime("%Y-%m-%d %H:%M")
    end=d["end_time"].astimezone(ZoneInfo(d["timezone"])).strftime("%Y-%m-%d %H:%M")
    return f"🔍 بررسی نهایی چالش\n\n🎯 {d['title']}\n📢 {d['channel_link']}\n👤 مالک: {d['owner_username']}\n🌍 {d['timezone']}\n🟢 شروع: {start}\n🔴 پایان: {end}\n⏳ مدت: {d['duration_hours']} ساعت\n\n{prizes}\n\n📜 قوانین:\n{d.get('rules') or 'ندارد'}\n⭐️ Stars: {'فعال' if d.get('stars_enabled') else 'غیرفعال'}"

async def show_preview(msg,context):
    await msg.reply_text(preview_text(owner_state(context)),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید و ساخت",callback_data="preview_confirm"),InlineKeyboardButton("✏️ لغو",callback_data="preview_cancel")]]))

async def preview_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa")
    if q.data=="preview_cancel": context.user_data.pop("new_challenge",None); context.user_data["state"]=None; await q.message.reply_text("لغو شد. از منو دوباره شروع کن."); return
    d=owner_state(context); owner=update.effective_user; cid=create_challenge(owner.id,d["owner_username"],d)
    me=await context.bot.get_me(); link=f"https://t.me/{me.username}?start=CH{cid}"
    text=f"🌟 {d['title']} 🌟\n\n"+"\n".join(f"🏆 نفر {i+1}: {p}" for i,p in enumerate(d["prizes"]))+f"\n\n⏳ مدت: {d['duration_hours']} ساعت\n🔗 ثبت‌نام: {link}\n📢 کانال: {d['channel_link']}\n👤 مالک: {d['owner_username']}"
    if d.get("rules"): text+=f"\n\n📜 قوانین:\n{d['rules']}"
    sent=await context.bot.send_message(d["channel_id"],text)
    try: await context.bot.pin_chat_message(d["channel_id"],sent.message_id)
    except Exception: pass
    context.user_data.clear(); context.user_data["lang"]=lang
    await q.message.reply_text(t(lang,"created")+f"\n🔗 {link}")

async def my_challenges(update,context):
    q=update.callback_query; await q.answer(); uid=update.effective_user.id; lang=context.user_data.get("lang","fa"); docs=list(challenges.find({"owner_id":uid}).sort("created_at",-1).limit(10))
    if not docs: await q.message.reply_text(t(lang,"none")); return
    rows=[]
    for d in docs:
        rows.append([InlineKeyboardButton(("🟢 " if d.get("active") else "🔴 ")+d["title"][:30],callback_data=f"cstats_{d['_id']}")])
    await q.message.reply_text("🎯 چالش‌های من:",reply_markup=InlineKeyboardMarkup(rows))

async def challenge_stats_callback(update,context):
    q=update.callback_query; await q.answer(); cid=q.data.split("_",1)[1]; d=get_challenge(cid)
    if not d or d["owner_id"]!=update.effective_user.id: return
    s=challenge_stats(cid); await q.message.reply_text(f"📊 {d['title']}\n\n👥 ثبت‌نام: {s['participants']}\n🔗 ورود از لینک: {s['starts']}\n📢 عضو کانال: {s['joined']}\n❤️ لایک‌ها: {s['likes']}\n⏰ وضعیت: {'فعال' if d['active'] else 'پایان‌یافته'}")

async def my_user_stats(update,context):
    q=update.callback_query; await q.answer(); uid=update.effective_user.id; count=participants.count_documents({"user_id":uid}); active=0
    for p in participants.find({"user_id":uid}):
        d=get_challenge(p["challenge_id"])
        active += bool(d and d.get("active"))
    await q.message.reply_text(f"📊 آمار من\n\n🎯 تعداد چالش‌ها: {count}\n🟢 فعال: {active}")
