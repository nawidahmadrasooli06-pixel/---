from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re
import jdatetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import create_challenge, get_challenge, owner_challenges, participants, is_blocked, audit

TZS={"af":"Asia/Kabul","ir":"Asia/Tehran","de":"Europe/Berlin"}
WEEK_FA=["دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه","شنبه","یکشنبه"]
WEEK_EN=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def owner_panel_keyboard(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"new"),callback_data="owner_new")],[InlineKeyboardButton(t(lang,"my_challenges"),callback_data="owner_list")],[InlineKeyboardButton(t(lang,"about"),callback_data="about")]])

async def owner_panel(update,context):
    lang=context.user_data.get("lang","fa")
    if is_blocked(update.effective_user.id): return
    await update.effective_message.reply_text(t(lang,"owner_panel"),reply_markup=owner_panel_keyboard(lang))

async def start_owner_flow(update,context):
    lang=context.user_data.get("lang","fa")
    if is_blocked(update.effective_user.id): return
    context.user_data.clear(); context.user_data["lang"]=lang; context.user_data["state"]="owner_title"; context.user_data["new_challenge"]={}
    await update.effective_message.reply_text(t(lang,"ask_title"))

async def owner_new_callback(update,context):
    await update.callback_query.answer(); await start_owner_flow(update,context)

async def receive_title(update,context):
    context.user_data["new_challenge"]["title"]=update.message.text.strip()[:120]; context.user_data["state"]="owner_channel"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_channel"))

async def receive_channel(update,context):
    lang=context.user_data.get("lang","fa"); raw=update.message.text.strip()
    if raw.startswith("https://t.me/"): raw="@"+raw.rstrip("/").split("/")[-1].lstrip("@")
    try:
        chat=await context.bot.get_chat(raw)
        member=await context.bot.get_chat_member(chat.id,context.bot.id)
        if member.status not in ("administrator","creator"): raise RuntimeError
    except Exception:
        await update.message.reply_text(t(lang,"bot_not_admin")); return
    data=context.user_data["new_challenge"]; data["channel_id"]=chat.id; data["channel_username"]=chat.username or ""; data["channel_link"]=f"https://t.me/{chat.username}" if chat.username else raw
    context.user_data["state"]="owner_username"; await update.message.reply_text(t(lang,"ask_owner"))

async def receive_owner_username(update,context):
    u=update.message.text.strip(); context.user_data["new_challenge"]["owner_username"]=u if u.startswith("@") else "@"+u; context.user_data["state"]="owner_winners"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_winners"))

async def receive_winners_count(update,context):
    lang=context.user_data.get("lang","fa")
    try: n=int(update.message.text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789"))); assert 1<=n<=20
    except Exception: await update.message.reply_text(t(lang,"invalid_number")); return
    context.user_data["new_challenge"]["winners_count"]=n; context.user_data["new_challenge"]["prizes"]=[]; context.user_data["prize_rank"]=1; context.user_data["state"]="owner_prize"; await update.message.reply_text(t(lang,"ask_prize",rank=1))

async def receive_prize(update,context):
    data=context.user_data["new_challenge"]; data["prizes"].append(update.message.text.strip()[:200]); rank=context.user_data["prize_rank"]+1
    if rank<=data["winners_count"]: context.user_data["prize_rank"]=rank; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_prize",rank=rank)); return
    context.user_data["state"]="owner_timezone"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_timezone"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context.user_data.get("lang","fa"),"tz_af"),callback_data="tz_af"),InlineKeyboardButton(t(context.user_data.get("lang","fa"),"tz_ir"),callback_data="tz_ir")],[InlineKeyboardButton(t(context.user_data.get("lang","fa"),"tz_de"),callback_data="tz_de")]]))

async def timezone_callback(update,context):
    q=update.callback_query; await q.answer(); tz=q.data.split("_",1)[1]; context.user_data["new_challenge"]["timezone"]=TZS[tz]; context.user_data["state"]="owner_date"; await send_date_choices(q.message,context)

async def send_date_choices(message,context):
    lang=context.user_data.get("lang","fa"); tz=ZoneInfo(context.user_data["new_challenge"]["timezone"]); today=datetime.now(tz).date(); rows=[]
    for i in range(7):
        d=today+timedelta(days=i); label=(WEEK_FA if lang=="fa" else WEEK_EN)[d.weekday()]+f" {d.isoformat()}"; rows.append([InlineKeyboardButton(label,callback_data=f"date_{d.isoformat()}")])
    rows.append([InlineKeyboardButton(t(lang,"other_date"),callback_data="date_manual")]); await message.reply_text(t(lang,"ask_date"),reply_markup=InlineKeyboardMarkup(rows))

async def date_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa")
    if q.data=="date_manual": context.user_data["state"]="owner_manual_date"; await q.message.reply_text(t(lang,"ask_manual_date")); return
    context.user_data["new_challenge"]["local_date"]=q.data.split("_",1)[1]; context.user_data["state"]="owner_time"; await q.message.reply_text(t(lang,"ask_time"))

async def receive_manual_date(update,context):
    lang=context.user_data.get("lang","fa"); s=update.message.text.strip().replace("-","/")
    try:
        parts=[int(x) for x in s.split("/")]
        if len(parts)!=3: raise ValueError
        if parts[0]>=1300 and parts[0]<1500:
            gd=jdatetime.date(parts[0],parts[1],parts[2]).togregorian(); date=gd
        else: date=datetime(parts[0],parts[1],parts[2]).date()
        context.user_data["new_challenge"]["local_date"]=date.isoformat(); context.user_data["state"]="owner_time"; await update.message.reply_text(t(lang,"ask_time"))
    except Exception: await update.message.reply_text(t(lang,"invalid_date"))

def parse_time(raw):
    s=raw.strip().lower().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789"))
    am=None
    if any(x in s for x in ("عصر","شب","pm")): am="pm"
    if any(x in s for x in ("صبح","am")): am="am"
    s=re.sub(r"(صبح|عصر|شب|am|pm)","",s).strip()
    if ":" in s: h,m=s.split(":",1)
    else: h,m=s,"0"
    h=int(h); m=int(m)
    if am:
        if not 1<=h<=12 or not 0<=m<=59: raise ValueError
        if am=="pm" and h<12: h+=12
        if am=="am" and h==12: h=0
    elif not 0<=h<=23 or not 0<=m<=59: raise ValueError
    return h,m

async def receive_time(update,context):
    lang=context.user_data.get("lang","fa")
    try: h,m=parse_time(update.message.text)
    except Exception: await update.message.reply_text(t(lang,"invalid_time")); return
    data=context.user_data["new_challenge"]; tz=ZoneInfo(data["timezone"]); local=datetime.fromisoformat(data["local_date"]).replace(hour=h,minute=m,tzinfo=tz); now=datetime.now(tz)
    if local<=now: await update.message.reply_text(t(lang,"past_date")); return
    data["start_time"]=local.astimezone(timezone.utc).replace(tzinfo=None); context.user_data["state"]="owner_duration"; await update.message.reply_text(t(lang,"ask_duration"))

async def receive_duration(update,context):
    lang=context.user_data.get("lang","fa")
    try: hours=float(update.message.text.strip().replace(",",".")); assert hours>0 and hours<=720
    except Exception: await update.message.reply_text(t(lang,"duration_invalid")); return
    data=context.user_data["new_challenge"]; data["duration_hours"]=hours; data["end_time"]=data["start_time"]+timedelta(hours=hours); context.user_data["state"]="owner_rules"; await update.message.reply_text(t(lang,"ask_rules"))

async def receive_rules(update,context):
    text=update.message.text.strip(); context.user_data["new_challenge"]["rules"]=t(context.user_data.get("lang","fa"),"default_rules") if text.lower() in ("پیش‌فرض","پیشفرض","default") else text[:1000]; context.user_data["state"]="owner_stars"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_stars"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context.user_data.get("lang","fa"),"yes"),callback_data="stars_yes"),InlineKeyboardButton(t(context.user_data.get("lang","fa"),"no"),callback_data="stars_no")]]))

async def stars_toggle_callback(update,context):
    q=update.callback_query; await q.answer(); data=context.user_data["new_challenge"]; lang=context.user_data.get("lang","fa")
    if q.data=="stars_yes": data["stars_enabled"]=True; context.user_data["state"]="owner_stars_rate"; await q.message.reply_text(t(lang,"ask_stars_rate"))
    else: data["stars_enabled"]=False; data["stars_rate"]=0; context.user_data["state"]=None; await show_preview(q.message,context)

async def receive_stars_rate(update,context):
    lang=context.user_data.get("lang","fa")
    try: rate=int(update.message.text.strip()); assert rate>0 and rate<=100
    except Exception: await update.message.reply_text(t(lang,"invalid_number")); return
    context.user_data["new_challenge"]["stars_rate"]=rate; context.user_data["state"]=None; await show_preview(update.message,context)

async def show_preview(message,context):
    d=context.user_data["new_challenge"]; lang=context.user_data.get("lang","fa"); tz=ZoneInfo(d["timezone"]); st=d["start_time"].replace(tzinfo=timezone.utc).astimezone(tz); en=d["end_time"].replace(tzinfo=timezone.utc).astimezone(tz)
    preview=f"🎯 {d['title']}\n📢 {d['channel_link']}\n👑 {d['owner_username']}\n🕐 {d['timezone']}\n📅 {st:%Y-%m-%d %H:%M} → {en:%Y-%m-%d %H:%M}\n⏳ {d['duration_hours']} ساعت\n\n"+"\n".join(f"🏆 {i+1}. {p}" for i,p in enumerate(d['prizes']))+f"\n\n⭐ {('فعال، '+str(d.get('stars_rate',0))+' لایک برای هر استار') if d.get('stars_enabled') else 'غیرفعال'}\n\n📜 {d['rules']}"
    await message.reply_text(t(lang,"preview",preview=preview),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"confirm"),callback_data="preview_confirm"),InlineKeyboardButton(t(lang,"edit"),callback_data="preview_edit")]]))

async def preview_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa")
    if q.data=="preview_edit": context.user_data.clear(); context.user_data["lang"]=lang; await q.message.reply_text("لغو شد. دوباره از «ساخت چالش» شروع کن.",reply_markup=owner_panel_keyboard(lang)); return
    d=context.user_data["new_challenge"]; owner_id=update.effective_user.id; owner_username=d["owner_username"]
    cid=create_challenge(owner_id,owner_username,d); reg=f"https://t.me/{context.bot.username}?start=CH{cid}"; d["registration_link"]=reg
    banner=(f"🌟 چالش لایکی جدید\n\n🎯 {d['title']}\n\n🏆 برنده‌ها و جوایز\n"+"\n".join(f"🥇 نفر {i+1}: {p}" for i,p in enumerate(d['prizes']))+f"\n\n📅 شروع: {d['start_time']} UTC\n⏳ مدت: {d['duration_hours']} ساعت\n⭐ هر استار: {d.get('stars_rate',0)} لایک\n\n📜 قوانین\n{d['rules']}\n\n📢 کانال: {d['channel_link']}\n👑 مالک: {owner_username}\n🎯 ثبت‌نام: {reg}\n\n❤️ چالش لایکی ما فرق داره؛ منتظر چالش‌های بعدی باشید!")
    sent=await context.bot.send_message(d["channel_id"],banner); 
    try: await context.bot.pin_chat_message(d["channel_id"],sent.message_id)
    except Exception: pass
    audit(owner_id,"challenge_created",cid,details=d["title"])
    context.user_data.clear(); context.user_data["lang"]=lang
    await q.message.reply_text(t(lang,"published",link=reg),reply_markup=owner_panel_keyboard(lang))

async def my_challenges(update,context):
    lang=context.user_data.get("lang","fa"); docs=owner_challenges(update.effective_user.id)
    if not docs: await update.effective_message.reply_text(t(lang,"no_challenges")); return
    buttons=[[InlineKeyboardButton(f"🎯 {d.get('title','چالش')}",callback_data=f"ownerch_{d['_id']}")] for d in docs[:20]]
    await update.effective_message.reply_text(t(lang,"my_challenges"),reply_markup=InlineKeyboardMarkup(buttons))

async def owner_challenge_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa"); cid=q.data.split("_",1)[1]; ch=get_challenge(cid)
    if not ch or ch.get("owner_id")!=update.effective_user.id: return
    ps=list(participants.find({"challenge_id":cid})); likes=sum(p.get("likes",0) for p in ps); stars=sum(p.get("stars_received",0) for p in ps); score=sum(p.get("likes",0)+p.get("stars_received",0)*ch.get("stars_rate",0) for p in ps)
    status="🟢 فعال" if ch.get("active") else "🔴 پایان‌یافته"; await q.message.reply_text(t(lang,"owner_stats",title=ch.get("title","-"),participants=len(ps),starts=ch.get("deep_link_starts",0),likes=likes,stars=stars,score=score,status=status))
