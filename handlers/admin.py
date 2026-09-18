from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import get_total_starts, challenges, get_open_reports, close_report, get_report, audit, block_user


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"), InlineKeyboardButton("🎯 چالش‌ها", callback_data="admin_challenges")],
        [InlineKeyboardButton("🚨 گزارش‌ها", callback_data="admin_reports")],
        [InlineKeyboardButton("↩️ برگشت", callback_data="menu_back")],
    ])

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(f"📊 آمار ربات\n\n👥 کاربران: {get_total_starts()}\n🎯 کل چالش‌ها: {challenges.count_documents({})}\n🟢 فعال: {challenges.count_documents({'active': True})}\n🏁 تمام‌شده: {challenges.count_documents({'active': False})}")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استفاده: /block <user_id>"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ آیدی عددی درست نیست."); return
    block_user(uid); audit(ADMIN_ID, "user_blocked", target_user_id=uid)
    await update.message.reply_text("⛔ کاربر مسدود شد.")

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔", show_alert=True); return
    await q.answer()
    await q.message.edit_text("🛡️ مدیریت مرکزی\n\nاز این بخش وضعیت ربات و گزارش‌ها را بررسی کن.", reply_markup=admin_keyboard())

async def dispatch_admin_callback(update, context):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔", show_alert=True); return
    data = q.data
    if data == "admin_panel": return await admin_panel_callback(update, context)
    if data == "admin_stats":
        await q.answer(); await q.message.edit_text(f"📊 کاربران: {get_total_starts()}\n🎯 کل چالش‌ها: {challenges.count_documents({})}\n🟢 فعال: {challenges.count_documents({'active': True})}\n🏁 پایان‌یافته: {challenges.count_documents({'active': False})}", reply_markup=admin_keyboard()); return
    if data == "admin_challenges":
        await q.answer(); docs = list(challenges.find({"active": True}).sort("created_at", -1).limit(30))
        text = "🎯 چالش‌های فعال:\n\n" + ("\n".join(f"• {c.get('title','-')} | {c.get('channel_link','-')}" for c in docs) if docs else "فعلاً چالشی نیست.")
        await q.message.edit_text(text, reply_markup=admin_keyboard()); return
    if data == "admin_reports":
        await q.answer(); rs = get_open_reports()
        if not rs:
            await q.message.edit_text("🚨 گزارش باز وجود ندارد.", reply_markup=admin_keyboard()); return
        rows = [[InlineKeyboardButton(f"🚨 {str(r['_id'])[-6:]} | {r.get('reason','other')}", callback_data=f"admin_report_{r['_id']}")] for r in rs]
        rows.append([InlineKeyboardButton("↩️ برگشت", callback_data="admin_panel")])
        await q.message.edit_text("🚨 گزارش‌های باز:", reply_markup=InlineKeyboardMarkup(rows)); return
    if data.startswith("admin_report_"):
        report_id = data[len("admin_report_"):]
        r = get_report(report_id)
        if not r:
            await q.answer("پیدا نشد", show_alert=True); return
        await q.answer()
        text = f"🚨 جزئیات گزارش\n\n🎯 چالش: {r.get('challenge_id')}\n👤 گزارش‌دهنده: {r.get('reporter_id')}\n👑 مالک: {r.get('owner_id')}\n📝 دلیل: {r.get('reason')}\n📄 توضیح: {r.get('details')}\n🆔 {r['_id']}"
        await q.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ بستن گزارش", callback_data=f"admin_close_report_{report_id}")], [InlineKeyboardButton("↩️ گزارش‌ها", callback_data="admin_reports")]])); return
    if data.startswith("admin_close_report_"):
        report_id = data[len("admin_close_report_"):]
        close_report(report_id); audit(ADMIN_ID, "report_closed", details={"report_id": report_id})
        await q.answer("گزارش بسته شد"); await q.message.edit_text("✅ گزارش بسته شد.", reply_markup=admin_keyboard())
