from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lang import t
from database import add_participant, get_challenge, participant_exists, set_participant_post, participants, now_utc

async def enter_participant_flow(update,context):
    lang=context.user_data.get("lang","fa"); cid=context.user_data.get("pending_challenge_id"); ch=get_challenge(cid)
    if not ch or not ch.get("active"): await update.callback_query.message.reply_text(t(lang,"not_found")); return
    old=participant_exists(cid,update.effective_user.id)
    if old: await update.callback_query.message.reply_text(t(lang,"already_registered")); return
    context.user_data["state"]="await_name"; await update.callback_query.message.reply_text(t(lang,"ask_name"))

async def receive_name(update,context):
    context.user_data["p_name"]=update.message.text.strip()[:100]; context.user_data["state"]="await_residence"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_residence"))
async def receive_residence(update,context):
    context.user_data["p_residence"]=update.message.text.strip()[:100]; context.user_data["state"]="await_photo"; await update.message.reply_text(t(context.user_data.get("lang","fa"),"ask_photo"))

async def receive_photo(update,context):
    lang=context.user_data.get("lang","fa"); cid=context.user_data.get("pending_challenge_id"); ch=get_challenge(cid)
    if not update.message.photo: await update.message.reply_text(t(lang,"ask_photo")); return
    if not ch or not ch.get("active"): await update.message.reply_text(t(lang,"not_found")); return
    user=update.effective_user; old=participant_exists(cid,user.id)
    if old: await update.message.reply_text(t(lang,"already_registered")); return
    num,created,_=add_participant(cid,user.id,context.user_data["p_name"],context.user_data["p_residence"],update.message.photo[-1].file_id,ch["channel_id"])
    if not created: await update.message.reply_text(t(lang,"already_registered")); return
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("❤️ لایک (0)",callback_data=f"like_{cid}_{num}")],[InlineKeyboardButton("🚨 گزارش چالش",callback_data=f"report_{cid}")]])
    caption=f"👤 اشتراک‌کننده: {num}\n\n👍 اسم: {context.user_data['p_name']}\n📍 محل: {context.user_data['p_residence']}\n\n🏆 برنده‌ها و جایزه‌ها:\n"+"\n".join(f"{i+1}. {p}" for i,p in enumerate(ch.get("prizes",[])))+f"\n\n🔗 ثبت‌نام: https://t.me/{(await context.bot.get_me()).username}?start=CH{cid}\n📢 کانال: {ch.get('channel_link','')}\n👤 مالک: {ch.get('owner_username','')}"
    sent=await context.bot.send_photo(ch["channel_id"],update.message.photo[-1].file_id,caption=caption,reply_markup=kb)
    set_participant_post(cid,num,sent.message_id)
    await update.message.reply_text(t(lang,"registered",number=num,residence=context.user_data["p_residence"]))
    for k in ("state","pending_challenge_id","p_name","p_residence"): context.user_data.pop(k,None)
