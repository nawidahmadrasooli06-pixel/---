from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bson import ObjectId
from lang import t
from database import participants, challenges, add_like, remove_like_on_leave, set_joined_status, get_challenge


async def like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    parts = query.data.split("_", 2)
    if len(parts) != 3:
        await query.answer("Invalid", show_alert=True); return
    _, challenge_id, participant_id = parts
    try:
        p = participants.find_one({"_id": ObjectId(participant_id), "challenge_id": challenge_id})
    except Exception:
        p = None
    if not p:
        await query.answer("پیدا نشد", show_alert=True); return
    challenge = get_challenge(challenge_id)
    if not challenge or not challenge.get("active"):
        await query.answer(t(lang, "challenge_closed"), show_alert=True); return
    if p.get("user_id") == query.from_user.id:
        await query.answer(t(lang, "cannot_like_self"), show_alert=True); return
    try:
        member = await context.bot.get_chat_member(challenge["channel_id"], query.from_user.id)
        is_member = member.status in ("member", "administrator", "creator")
        if is_member:
            set_joined_status(challenge_id, query.from_user.id, True)
    except Exception:
        is_member = False
    if not is_member:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "joined_check"), callback_data=query.data)]])
        await query.answer(t(lang, "channel_required"), show_alert=True)
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass
        return
    success, reason = add_like(p["_id"], query.from_user.id)
    if not success:
        await query.answer(t(lang, "already_liked") if reason == "duplicate" else "خطا", show_alert=False)
        return
    updated = participants.find_one({"_id": p["_id"]})
    await query.answer(t(lang, "like_added"))
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"❤️ لایک ({updated.get('likes',0)})", callback_data=query.data)]]))
    except Exception:
        pass


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member
    if not cm:
        return
    old_status = cm.old_chat_member.status
    new_status = cm.new_chat_member.status
    user_id = cm.new_chat_member.user.id
    channel_id = cm.chat.id
    if new_status in ("left", "kicked") and old_status in ("member", "administrator", "creator"):
        remove_like_on_leave(channel_id, user_id)
    elif new_status in ("member", "administrator", "creator"):
        participants.update_many({"channel_id": channel_id, "user_id": user_id}, {"$set": {"joined_channel": True}})
