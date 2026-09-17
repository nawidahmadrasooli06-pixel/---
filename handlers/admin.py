from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import *

def ok(update): return bool(ADMIN_ID and update.effective_user and update.effective_user.id==ADMIN_ID)
async def stats_command(update,context):
    if not ok(update): return
    await update.message.reply_text(f"👑 Super Admin\n\n👥 کاربران: {users.count_documents({})}\n🎯 چالش‌ها: {challenges.count_documents({})}\n🟢 فعال: {challenges.count_documents({'active':True})}\n👤 ثبت‌نام‌ها: {participants.count_documents({})}\n🚨 گزارش‌ها: {reports.count_documents({'status':{'$ne':'closed'}})}")
async def block_command(update,context):
    if not ok(update) or not context.args: return
    try: uid=int(context.args[0])
    except Exception: await update.message.reply_text("/block USER_ID"); return
    set_blocked(uid,True); audit(ADMIN_ID,"block_user",target_user_id=uid); await update.message.reply_text(f"⛔ کاربر {uid} مسدود شد.")
async def unblock_command(update,context):
    if not ok(update) or not context.args: return
    uid=int(context.args[0]); set_blocked(uid,False); audit(ADMIN_ID,"unblock_user",target_user_id=uid); await update.message.reply_text(f"🔓 کاربر {uid} آزاد شد.")
async def admin_panel(update,context):
    if not ok(update): return
    await update.message.reply_text("👑 پنل Super Admin\n/stats\n/block USER_ID\n/unblock USER_ID\n/reports")
async def reports_command(update,context):
    if not ok(update): return
    docs=list(reports.find({"status":{"$ne":"closed"}}).sort("created_at",-1).limit(20));
    if not docs: await update.message.reply_text("🚨 گزارشی نیست."); return
    text="🚨 گزارش‌ها:\n\n"+"\n".join(f"#{str(x['_id'])[-6:]} | چالش {x.get('challenge_id')} | {x.get('reason')} | کاربر {x.get('reporter_id')}" for x in docs)
    await update.message.reply_text(text)
async def report_callback(update,context):
    q=update.callback_query; await q.answer(); cid=q.data.split("_",1)[1]
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 جایزه پرداخت نشده",callback_data=f"rreason_{cid}_prize"),InlineKeyboardButton("⚠️ مشکل اجرا",callback_data=f"rreason_{cid}_problem")],[InlineKeyboardButton("🔄 اطلاعات تغییر کرده",callback_data=f"rreason_{cid}_changed"),InlineKeyboardButton("🚨 رفتار مشکوک",callback_data=f"rreason_{cid}_suspicious")]])
    await q.message.reply_text("دلیل گزارش را انتخاب کن:",reply_markup=kb)
async def report_reason_callback(update,context):
    q=update.callback_query; await q.answer(); _,cid,reason=q.data.split("_",2); reports.insert_one({"challenge_id":cid,"reporter_id":q.from_user.id,"reason":reason,"status":"open","created_at":now_utc()}); audit(q.from_user.id,"report_created",cid,details=reason)
    if ADMIN_ID: await context.bot.send_message(ADMIN_ID,f"🚨 گزارش جدید\nچالش: {cid}\nکاربر: {q.from_user.id}\nدلیل: {reason}")
    await q.message.reply_text("گزارش ثبت شد. بررسی می‌شود.")
