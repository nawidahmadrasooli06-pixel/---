from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from lang import t
from database import add_participant, challenges

NAME, AGE, CITY, PHOTO = range(4)

async def enter_participant_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    query = update.callback_query
    await query.message.reply_text(t(lang, "ask_name"))
    return NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["p_name"] = update.message.text.strip()
    await update.message.reply_text(t(lang, "ask_age"))
    return AGE

async def receive_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["p_age"] = update.message.text.strip()
    await update.message.reply_text(t(lang, "ask_city"))
    return CITY

async def receive_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    context.user_data["p_city"] = update.message.text.strip()
    await update.message.reply_text(t(lang, "ask_photo"))
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    if not update.message.photo:
        await update.message.reply_text(t(lang, "ask_photo"))
        return PHOTO
    photo_file_id = update.message.photo[-1].file_id

    challenge_id = context.user_data.get("pending_challenge_id")
    challenge = challenges.find_one({"_id": __import__("bson").ObjectId(challenge_id)})
    if not challenge:
        await update.message.reply_text("چالش پیدا نشد یا تموم شده.")
        return ConversationHandler.END

    user = update.effective_user
    number = add_participant(
        challenge_id, user.id,
        context.user_data["p_name"], context.user_data["p_age"],
        context.user_data["p_city"], photo_file_id
    )

    caption = (
        f"👤 شرکت‌کننده شماره {number}\n"
        f"نام: {context.user_data['p_name']}\n"
        f"سن: {context.user_data['p_age']}\n"
        f"شهر: {context.user_data['p_city']}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ لایک (0)", callback_data=f"like_{challenge_id}_{number}")
    ]])
    sent = await context.bot.send_photo(
        chat_id=challenge["channel_id"], photo=photo_file_id,
        caption=caption, reply_markup=kb
    )

    from database import participants
    participants.update_one(
        {"challenge_id": challenge_id, "number": number},
        {"$set": {"post_message_id": sent.message_id}}
    )

    await update.message.reply_text(t(lang, "registered", number=number))
    return ConversationHandler.END

participant_conversation_handler = ConversationHandler(
    entry_points=[],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_age)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_city)],
        PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
    },
    fallbacks=[],
    per_message=False
)
