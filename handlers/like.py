from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import participants, add_like, remove_like_on_leave, get_challenge
from lang import t

async def like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; lang=context.user_data.get("lang","fa")
    _,cid,number=q.data.split("_"); number=int(number)
    p=participants.find_one({"challenge_id":cid,"number":number}); ch=get_challenge(cid)
    if not p or not ch: await q.answer("پیدا نشد",show_alert=True); return
    try:
        member=await context.bot.get_chat_member(ch["channel_id"],q.from_user.id); is_member=member.status in ("member","administrator","creator")
    except Exception: is_member=False
    if not is_member: await q.answer(t(lang,"must_join"),show_alert=True); return
    if not add_like(p["_id"],q.from_user.id): await q.answer(t(lang,"already_liked"),show_alert=True); return
    updated=participants.find_one({"_id":p["_id"]})
    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"like_button",count=updated.get("likes",0)),callback_data=q.data)]]))
    await q.answer(t(lang,"liked"))

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm=update.chat_member
    if cm.new_chat_member.status in ("left","kicked") and cm.old_chat_member.status in ("member","administrator"):
        remove_like_on_leave(cm.chat.id,cm.new_chat_member.user.id)
