from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import get_total_starts, challenges, get_open_reports, close_report, audit


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"), InlineKeyboardButton("🎯 چالش‌ها", callback_data="admin_challenges")],
        [InlineKeyboardButton("🚨 گزارش‌ها", callback_data="admin_reports")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="menu_back")],
    ])


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 آمار ربات\n\n👥 کاربران: {get_total_starts()}\n🎯 کل چالش‌ها: {challenges.count_documents({})}\n🟢 فعال: {challenges.count_documents({'active': True})}\n🏁 تمام‌شده: {challenges.count_documents({'active': False})}"
    )


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /block <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("آیدی عددی درست نیست."); return
    from database import db
    db["blocked_users"].update_one({"user_id": user_id}, {"$set": {"user_id": user_id, "blocked": True}}, upsert=True)
    await update.message.reply_text("⛔ کاربر مسدود شد.")


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    await query.answer()
    await query.message.reply_text("🛡️ مدیریت مرکزی\n\nاز این بخش می‌توانی وضعیت کلی ربات و گزارش‌ها را بررسی کنی.", reply_markup=admin_keyboard())


async def show_open_reports(query, context):
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    reports = get_open_reports()
    if not reports:
        await query.message.reply_text("🚨 گزارش باز وجود ندارد."); return
    rows = []
    for r in reports:
        rows.append([InlineKeyboardButton(f"🚨 {str(r['_id'])[-6:]} | {r.get('reason','other')}", callback_data=f"admin_report_{r['_id']}")])
    await query.message.reply_text("🚨 گزارش‌های باز:", reply_markup=InlineKeyboardMarkup(rows))


async def admin_report_detail(query, context, report_id):
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    from bson import ObjectId
    from database import reports
    r = reports.find_one({"_id": ObjectId(report_id)})
    if not r:
        await query.message.reply_text("گزارش پیدا نشد."); return
    text = (
        "🚨 جزئیات گزارش\n\n"
        f"🎯 چالش: {r.get('challenge_id')}\n"
        f"👤 گزارش‌دهنده: {r.get('reporter_id')}\n"
        f"👑 مالک: {r.get('owner_id')}\n"
        f"📝 دلیل: {r.get('reason')}\n"
        f"📄 توضیح: {r.get('details')}\n"
        f"🆔 {r['_id']}"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ بستن گزارش", callback_data=f"admin_close_report_{report_id}")]])
    await query.message.reply_text(text, reply_markup=kb)


async def close_report_callback(query, context, report_id):
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    close_report(report_id)
    audit(ADMIN_ID, "report_closed", details={"report_id": report_id})
    await query.answer("گزارش بسته شد")
    await query.message.reply_text("✅ گزارش بسته شد.")


async def admin_stats_callback(query, context):
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    await query.answer()
    await query.message.reply_text(f"📊 کاربران: {get_total_starts()}\n🎯 چالش‌ها: {challenges.count_documents({})}\n🟢 فعال: {challenges.count_documents({'active': True})}\n🏁 پایان‌یافته: {challenges.count_documents({'active': False})}")


async def admin_challenges_callback(query, context):
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔", show_alert=True); return
    await query.answer()
    docs = list(challenges.find({"active": True}).sort("created_at", -1).limit(30))
    if not docs:
        await query.message.reply_text("🎯 چالش فعال وجود ندارد."); return
    lines = ["🎯 چالش‌های فعال:\n"]
    for c in docs:
        lines.append(f"• {c.get('title','-')} | {c.get('channel_link') or c.get('channel_username') or '-'}")
    await query.message.reply_text("\n".join(lines))
