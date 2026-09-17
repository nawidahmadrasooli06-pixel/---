
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import get_total_starts, challenges

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total_users = get_total_starts()
    total_challenges = challenges.count_documents({})
    active_challenges = challenges.count_documents({"active": True})
    await update.message.reply_text(
        f"📊 آمار ربات\n\n"
        f"👥 کل کاربرایی که /start زدن: {total_users}\n"
        f"🎯 کل چالش‌ها: {total_challenges}\n"
        f"✅ چالش‌های فعال: {active_challenges}"
    )

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /block <owner_id>")
        return
    owner_id = int(context.args[0])
    from database import db
    db["blocked_owners"].update_one(
        {"owner_id": owner_id}, {"$set": {"owner_id": owner_id, "blocked": True}}, upsert=True
    )
    await update.message.reply_text(f"مالک {owner_id} مسدود شد ✅")
