import asyncio
import logging
import os
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, MessageReactionHandler, filters

from config import BOT_TOKEN
from handlers.start import start_command, language_callback, menu_callback
from handlers.owner import owner_new_callback, timezone_callback, date_callback, stars_toggle_callback, preview_callback, owner_challenge_callback
from handlers.participant import report_challenge_callback, report_reason_callback
from handlers.like import like_callback, chat_member_update
from handlers.about import about_callback, creator_callback
from handlers.admin import stats_command, block_command, unblock_command, admin_panel, admin_callback, close_report_callback
from handlers.stars import message_reaction_count_update
from handlers.countdown import start_scheduler
from handlers.router import text_router, photo_router

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = b"OK" if self.path in ("/", "/health") else b"Not Found"
        self.send_response(200 if response == b"OK" else 404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    def log_message(self, format, *args):
        return

def start_health_server():
    port=int(os.environ.get("PORT","10000")); server=ThreadingHTTPServer(("0.0.0.0",port),HealthHandler); logger.info("Health server on %s",port); server.serve_forever()

def create_application():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start_command))
    app.add_handler(CommandHandler("stats",stats_command))
    app.add_handler(CommandHandler("block",block_command))
    app.add_handler(CommandHandler("unblock",unblock_command))
    app.add_handler(CommandHandler("admin",admin_panel))
    app.add_handler(CallbackQueryHandler(language_callback,pattern=r"^lang_(fa|en)$"))
    app.add_handler(CallbackQueryHandler(menu_callback,pattern=r"^menu_"))
    app.add_handler(CallbackQueryHandler(owner_new_callback,pattern=r"^owner_new$"))
    app.add_handler(CallbackQueryHandler(timezone_callback,pattern=r"^tz_(af|ir|de)$"))
    app.add_handler(CallbackQueryHandler(date_callback,pattern=r"^date_"))
    app.add_handler(CallbackQueryHandler(stars_toggle_callback,pattern=r"^stars_(yes|no)$"))
    app.add_handler(CallbackQueryHandler(preview_callback,pattern=r"^preview_(confirm|edit)$"))
    app.add_handler(CallbackQueryHandler(like_callback,pattern=r"^like_"))
    app.add_handler(CallbackQueryHandler(report_challenge_callback,pattern=r"^reportch_"))
    app.add_handler(CallbackQueryHandler(report_reason_callback,pattern=r"^reason_"))
    app.add_handler(CallbackQueryHandler(owner_challenge_callback,pattern=r"^ownerch_"))
    app.add_handler(CallbackQueryHandler(admin_panel,pattern=r"^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_callback,pattern=r"^admin_(stats|reports)$"))
    app.add_handler(CallbackQueryHandler(close_report_callback,pattern=r"^close_report_"))
    app.add_handler(CallbackQueryHandler(about_callback,pattern=r"^about$"))
    app.add_handler(CallbackQueryHandler(creator_callback,pattern=r"^creator$"))
    app.add_handler(MessageHandler(filters.PHOTO,photo_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_router))
    app.add_handler(ChatMemberHandler(chat_member_update,ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageReactionHandler(message_reaction_count_update,message_reaction_types=MessageReactionHandler.MESSAGE_REACTION_COUNT_UPDATED))
    return app

async def main():
    Thread(target=start_health_server,daemon=True).start()
    app=create_application()
    await app.initialize()
    scheduler=await start_scheduler(app.bot)
    app.bot_data["challenge_scheduler"]=scheduler
    await app.start()
    await app.updater.start_polling(allowed_updates=["message","callback_query","chat_member","message_reaction_count"])
    logger.info("Bot is live")
    try:
        while True: await asyncio.sleep(3600)
    finally:
        scheduler.shutdown(wait=False)
        await app.updater.stop(); await app.stop(); await app.shutdown()

if __name__=="__main__": asyncio.run(main())
