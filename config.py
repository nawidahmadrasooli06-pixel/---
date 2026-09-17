import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CREATOR_NAME = "〘Cactuc = نــوید〙"
CREATOR_USERNAME = "cactuc580"
CREATOR_ID_LINK = f"https://t.me/{CREATOR_USERNAME}"
DEFAULT_LANG = "fa"
SUPPORTED_LANGS = ["fa", "en", "ru", "ar"]
ADMIN_ID = 8659480577

