from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import participants, challenges, add_like, remove_like_on_leave, get_challenge
from bson import ObjectId

async def like_callback(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; parts=q.data.split("_"); cid=parts[1]; num=int(parts[2]); lang=context.user_data.get("lang","fa"); p=participants.find_one({"challenge_id":cid,"number":num}); ch=get_challenge(cid)
    if not p or not ch or not ch.get("active"): await q.answer(t(lang,"not_found"),show_alert=True); return
    try:
        m=await context.bot.get_chat_member(ch["channel_id"],q.from_user.id); joined=m.status in ("member","administrator","creator","restricted")
    except Exception: joined=False
    if not joined: await q.answer(t(lang,"must_join"),show_alert=True); return
    if not add_like(p["_id"],q.from_user.id): await q.answer(t(lang,"already_liked")); return
    updated=participants.find_one({"_id":p["_id"]}); await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"❤️ لایک ({updated.get('likes',0)})",callback_data=q.data)],[InlineKeyboardButton("🚨 گزارش چالش",callback_data=f"report_{cid}")]])); await q.answer(t(lang,"liked"))

async def chat_member_update(update:Update,context:ContextTypes.DEFAULT_TYPE):
    cm=update.chat_member
    if not cm: return
    old=cm.old_chat_member.status; new=cm.new_chat_member.status; uid=cm.new_chat_member.user.id
    if new in ("left","kicked") and old not in ("left","kicked"):
        remove_like_on_leave(cm.chat.id,uid)
    if new in ("member","administrator","creator","restricted"):
        participants.update_many({"channel_id":cm.chat.id,"user_id":uid},{"$set":{"joined_channel":True}})
    elif new in ("left","kicked"):
        participants.update_many({"channel_id":cm.chat.id,"user_id":uid},{"$set":{"joined_channel":False}})
