import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatMemberHandler, filters
)
from config import BOT_TOKEN
from handlers.start import start_command, language_callback, menu_callback
from handlers.owner import owner_conversation_handler
from handlers.participant import participant_conversation_handler
from handlers.like import like_callback, chat_member_update
from handlers.about import about_callback, creator_callback
from handlers.admin import stats_command, block_command
from handlers.countdown import start_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # دستورات اصلی
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("block", block_command))

    # مکالمه‌ی ساخت چالش توسط مالک
    app.add_handler(owner_conversation_handler)

    # مکالمه‌ی ثبت‌نام شرکت‌کننده
    app.add_handler(participant_conversation_handler)

    # دکمه‌های شیشه‌ای
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(like_callback, pattern="^like_"))
    app.add_handler(CallbackQueryHandler(about_callback, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(creator_callback, pattern="^creator$"))

    # تشخیص لفت‌دادن از کانال (برای کم‌کردن لایک)
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))

    # شروع تایمر شمارش معکوس و اعلام برنده‌ها
    start_scheduler(app.bot)

    logger.info("ربات روشن شد ✅")
    app.run_polling(allowed_updates=["message", "callback_query", "chat_member"])

if __name__ == "__main__":
    main()
