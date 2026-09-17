import logging
import os
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    MessageReactionHandler,
    filters
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
# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# ============================================================
# RENDER HEALTH SERVER
# ============================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            response = b"OK"
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(response))
            )
            self.end_headers()
            self.wfile.write(response)
        else:
            response = b"Not Found"
            self.send_response(404)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(response))
            )
            self.end_headers()
            self.wfile.write(response)
    def log_message(self, format, *args):
        return
def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )
    logger.info(
        f"Health server running on port {port}"
    )
    server.serve_forever()
# ============================================================
# MAIN BOT
# ============================================================
def main():
    # --------------------------------------------------------
    # Start Render HTTP health server
    # --------------------------------------------------------
    health_thread = Thread(
        target=start_health_server,
        daemon=True
    )
    health_thread.start()
    # --------------------------------------------------------
    # Telegram Application
    # --------------------------------------------------------
    app = Application.builder().token(BOT_TOKEN).build()
    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------
    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )
    app.add_handler(
        CommandHandler(
            "stats",
            stats_command
        )
    )
    app.add_handler(
        CommandHandler(
            "block",
            block_command
        )
    )
    # --------------------------------------------------------
    # Language / Menu callbacks
    # --------------------------------------------------------
    app.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern="^lang_"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern="^menu_"
        )
    )
    # --------------------------------------------------------
    # Owner callbacks
    # --------------------------------------------------------
    app.add_handler(
        CallbackQueryHandler(
            stars_toggle_callback,
            pattern="^stars_"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            preview_callback,
            pattern="^preview_"
        )
    )
    # --------------------------------------------------------
    # Like / About / Creator callbacks
    # --------------------------------------------------------
    app.add_handler(
        CallbackQueryHandler(
            like_callback,
            pattern="^like_"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            about_callback,
            pattern="^about$"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            creator_callback,
            pattern="^creator$"
        )
    )
    # --------------------------------------------------------
    # Text messages
    # --------------------------------------------------------
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )
    # --------------------------------------------------------
    # Photo messages
    # --------------------------------------------------------
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )
    # --------------------------------------------------------
    # Chat member updates
    # --------------------------------------------------------
    app.add_handler(
        ChatMemberHandler(
            chat_member_update,
            ChatMemberHandler.CHAT_MEMBER
        )
    )
    # --------------------------------------------------------
    # Message reaction updates
    # --------------------------------------------------------
    # IMPORTANT:
    # python-telegram-bot 21.6 uses
    # MESSAGE_REACTION_COUNT_UPDATED
    # --------------------------------------------------------
    app.add_handler(
        MessageReactionHandler(
            message_reaction_count_update,
            message_reaction_types=(
                MessageReactionHandler.MESSAGE_REACTION_COUNT_UPDATED
            )
        )
    )
    # --------------------------------------------------------
    # Countdown scheduler
    # --------------------------------------------------------
    start_scheduler(app.bot)
    logger.info("ربات روشن شد")
    # --------------------------------------------------------
    # Telegram polling
    # --------------------------------------------------------
    app.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "chat_member",
            "message_reaction_count"
        ]
    )
# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    main()
