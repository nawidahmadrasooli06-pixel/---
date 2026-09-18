from telegram import Update
from telegram.ext import ContextTypes
from database import participants, challenges, set_stars_received


async def message_reaction_count_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mrc = update.message_reaction_count
    if not mrc:
        return
    channel_id = mrc.chat.id
    message_id = mrc.message_id
    paid_count = 0
    for reaction in (mrc.reactions or []):
        try:
            reaction_type = reaction.type.type
        except Exception:
            reaction_type = ""
        if reaction_type == "paid":
            paid_count = int(reaction.total_count)
            break
    p = participants.find_one({"post_message_id": message_id, "channel_id": channel_id})
    if not p:
        return
    challenge = challenges.find_one({"_id": __import__('bson').ObjectId(p["challenge_id"])})
    if not challenge or not challenge.get("stars_enabled"):
        return
    # Telegram sends this update whenever the reaction count changes.
    # Store zero too, so removed Stars are reflected immediately.
    set_stars_received(p["_id"], paid_count)
