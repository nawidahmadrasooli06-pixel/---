from telegram import Update
from telegram.ext import ContextTypes
from database import participants, challenges
import bson

async def message_reaction_count_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    وقتی رو یه پست کانال واکنش ستاره‌ای (Paid Reaction) زده بشه،
    تلگرام این آپدیت رو می‌فرسته. اینجا فقط عدد رو می‌خونیم،
    هیچ پولی از ربات رد نمی‌شه.
    """
    mrc = update.message_reaction_count
    if not mrc:
        return

    channel_id = mrc.chat.id
    message_id = mrc.message_id

    paid_count = 0
    for reaction in mrc.reactions:
        if reaction.type.type == "paid":
            paid_count = reaction.total_count
            break

    if paid_count == 0:
        return

    p = participants.find_one({"post_message_id": message_id, "channel_id": channel_id})
    if not p:
        return

    ch = challenges.find_one({"_id": bson.ObjectId(p["challenge_id"])})
    if not ch or not ch.get("stars_enabled"):
        return

    rate = ch.get("stars_rate", 0)
    participants.update_one(
        {"_id": p["_id"]},
        {"$set": {"stars_received": paid_count}}
    )
