import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CREATOR_NAME = "نوید | Cactuc"
CREATOR_USERNAME = "cactuc580"
CREATOR_LINK = f"https://t.me/{CREATOR_USERNAME}"
DEFAULT_LANG = "fa"
SUPPORTED_LANGS = ["fa", "en", "ru", "ar"]

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set")
