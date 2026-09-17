import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatMemberHandler, MessageReactionHandler, filters
)
from config import BOT_TOKEN
from handlers.start import start_command, language_callback, menu_callback
from handlers.owner import stars_toggle_callback, preview_callback
from handlers.like import like_callback, chat_member_update
from handlers.about import about_callback, creator_callback
from handlers.admin import stats_command, block_command
from handlers.stars import message_reaction_count_update
from handlers.countdown import start_scheduler
from handlers.router import text_router, photo_router

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("block", block_command))

    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(stars_toggle_callback, pattern="^stars_"))
    app.add_handler(CallbackQueryHandler(preview_callback, pattern="^preview_"))
    app.add_handler(CallbackQueryHandler(like_callback, pattern="^like_"))
    app.add_handler(CallbackQueryHandler(about_callback, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(creator_callback, pattern="^creator$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))

    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageReactionHandler(
        message_reaction_count_update,
        message_reaction_types=MessageReactionHandler.MESSAGE_REACTION_COUNT_UPDATES
    ))

    start_scheduler(app.bot)

    logger.info("ربات روشن شد ✅")
    app.run_polling(allowed_updates=["message", "callback_query", "chat_member", "message_reaction_count"])

if __name__ == "__main__":
    main()
