from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import participants, add_like, remove_like_on_leave
import bson

async def like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    _, challenge_id, number = query.data.split("_")
    number = int(number)

    p = participants.find_one({"challenge_id": challenge_id, "number": number})
    if not p:
        await query.answer("پیدا نشد", show_alert=True)
        return

    from database import challenges
    challenge = challenges.find_one({"_id": bson.ObjectId(challenge_id)})
    channel_id = challenge["channel_id"]

    try:
        member = await context.bot.get_chat_member(channel_id, query.from_user.id)
        is_member = member.status in ("member", "administrator", "creator")
    except Exception:
        is_member = False

    if not is_member:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, "check_again"), callback_data=query.data)
        ]])
        await query.answer(t(lang, "must_join_first"), show_alert=True)
        return

    success = add_like(p["_id"], query.from_user.id)
    if not success:
        await query.answer(t(lang, "already_liked"))
        return

    updated = participants.find_one({"_id": p["_id"]})
    new_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"❤️ لایک ({updated['likes']})", callback_data=query.data)
    ]])
    await query.edit_message_reply_markup(reply_markup=new_kb)
    await query.answer(t(lang, "like_added"))

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member
    if cm.new_chat_member.status in ("left", "kicked") and cm.old_chat_member.status == "member":
        remove_like_on_leave(cm.chat.id, cm.new_chat_member.user.id)
        affected = participants.find({"liked_by": {"$ne": cm.new_chat_member.user.id}, "channel_id": cm.chat.id})
